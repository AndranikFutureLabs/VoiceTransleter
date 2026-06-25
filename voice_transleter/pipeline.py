from pathlib import Path
from transliterate import translit
from .audio_extractor import extract_audio
from .transcription import transcribe
from .translator import translate_segments
from .tts import synthesize_segments
from .video_renderer import merge_audio_segments, replace_audio_in_video
from .voice_cloner import get_voice_by_id
from config import TEMP_DIR

_EN_TO_RU_TRANSLIT = {
    'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г',
    'h': 'х', 'i': 'и', 'j': 'дж', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н',
    'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'w': 'в', 'x': 'кс', 'y': 'й', 'z': 'з',
    'sh': 'ш', 'ch': 'ч', 'th': 'з', 'ph': 'ф', 'gh': 'г', 'ng': 'нг',
    'tion': 'шн', 'ight': 'айт', 'ea': 'иа', 'ou': 'ау', 'oo': 'у',
}


def _transliterate_en(text: str) -> str:
    result = []
    i = 0
    text = text.lower()
    while i < len(text):
        matched = False
        for pat_len in (4, 3, 2):
            if i + pat_len <= len(text) and text[i:i+pat_len] in _EN_TO_RU_TRANSLIT:
                result.append(_EN_TO_RU_TRANSLIT[text[i:i+pat_len]])
                i += pat_len
                matched = True
                break
        if not matched:
            c = text[i]
            result.append(_EN_TO_RU_TRANSLIT.get(c, c))
            i += 1
    return ''.join(result)


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _save_text_files(segments: list[dict], video_path: Path):
    base = video_path.parent / video_path.stem
    entries = [
        ("_source.txt", "_source_plain.txt", lambda s: s['text']),
        ("_translation.txt", "_translation_plain.txt", lambda s: s['translated']),
        ("_source_translit.txt", "_source_translit_plain.txt", lambda s: _transliterate_en(s['text'])),
        ("_translation_translit.txt", "_translation_translit_plain.txt", lambda s: translit(s['translated'], 'ru', reversed=True)),
    ]
    for name_ts, name_plain, get_text in entries:
        lines_plain = []
        with open(f"{base}{name_ts}", "w", encoding="utf-8") as f_ts:
            for seg in segments:
                text = get_text(seg)
                line = f"[{_format_timestamp(seg['start'])} --> {_format_timestamp(seg['end'])}]"
                f_ts.write(f"{line}\n{text}\n\n")
                lines_plain.append(text)
        with open(f"{base}{name_plain}", "w", encoding="utf-8") as f_plain:
            f_plain.write("\n".join(lines_plain))


def dub_video(
    video_path: str | Path,
    source_lang: str = "en",
    voice_id: str = "silero_xenia",
    output_path: str | Path | None = None,
    keep_temp: bool = False,
    progress_callback=None,
) -> Path:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    voice_profile = get_voice_by_id(voice_id)
    if voice_profile is None:
        raise ValueError(f"Voice profile not found: {voice_id}")

    def log(msg):
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    log("[1/5] Extracting audio from video...")
    audio_path = extract_audio(video_path)

    log("[2/5] Transcribing audio...")
    segments = transcribe(str(audio_path), language=source_lang)
    log(f"       Found {len(segments)} segments")

    log("[3/5] Translating EN->RU...")
    translated = translate_segments(segments)

    log(f"[4/5] Synthesizing speech (voice: {voice_profile['name']})...")
    tts_segments = synthesize_segments(translated, voice_profile)

    log("[5/5] Assembling final video...")
    merged_audio = merge_audio_segments(tts_segments, TEMP_DIR / "merged.wav")
    result = replace_audio_in_video(video_path, merged_audio, output_path)

    log("Saving text files with timestamps...")
    _save_text_files(translated, result)

    if not keep_temp:
        import shutil
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

    log(f"Done! Output: {result}")
    return result
