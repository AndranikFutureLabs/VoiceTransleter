import subprocess
from pathlib import Path
from pydub import AudioSegment
from config import TEMP_DIR, OUTPUT_DIR, TTS_SAMPLE_RATE, OUTPUT_SAMPLE_RATE


def merge_audio_segments(segments: list[dict], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    silence = AudioSegment.silent(duration=0, frame_rate=TTS_SAMPLE_RATE)
    merged = AudioSegment.silent(duration=0, frame_rate=TTS_SAMPLE_RATE)

    prev_end = 0.0
    for seg in segments:
        gap_start = int(prev_end * 1000)
        seg_start = int(seg["start"] * 1000)

        if seg_start > gap_start:
            merged += AudioSegment.silent(
                duration=seg_start - gap_start, frame_rate=TTS_SAMPLE_RATE
            )
        elif seg_start < gap_start:
            merged = merged[:seg_start]

        seg_audio = AudioSegment.from_file(seg["audio_path"])
        merged += seg_audio

        prev_end = seg["end"]

    merged.export(str(output_path), format="wav", parameters=["-ar", str(OUTPUT_SAMPLE_RATE)])
    return output_path


def replace_audio_in_video(video_path: str | Path, new_audio_path: str | Path, output_path: str | Path | None = None) -> Path:
    video_path = Path(video_path)
    new_audio_path = Path(new_audio_path)

    if output_path is None:
        output_path = OUTPUT_DIR / f"{video_path.stem}_dubbed{video_path.suffix}"

    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    temp_video = TEMP_DIR / f"no_audio_{video_path.name}"
    temp_audio_aac = TEMP_DIR / "dubbed_audio.aac"

    cmd_rm_audio = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c", "copy",
        "-an",
        str(temp_video),
    ]
    subprocess.run(cmd_rm_audio, check=True, capture_output=True)

    cmd_convert = [
        "ffmpeg", "-y",
        "-i", str(new_audio_path),
        "-c:a", "aac",
        "-b:a", "192k",
        str(temp_audio_aac),
    ]
    subprocess.run(cmd_convert, check=True, capture_output=True)

    cmd_combine = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(temp_audio_aac),
        "-c", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd_combine, check=True, capture_output=True)

    temp_video.unlink(missing_ok=True)
    temp_audio_aac.unlink(missing_ok=True)

    return output_path
