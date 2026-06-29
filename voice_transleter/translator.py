from deep_translator import GoogleTranslator
from config import TRANSLATE_TARGET

_WHISPER_TO_GOOGLE = {
    "zh": "zh-CN",
    "he": "iw",
}


def _to_google_lang(code: str) -> str:
    return _WHISPER_TO_GOOGLE.get(code, code)


def translate_segments(segments: list[dict], source_lang: str, target_lang: str | None = None) -> list[dict]:
    if target_lang is None:
        target_lang = TRANSLATE_TARGET

    src = _to_google_lang(source_lang)
    tgt = _to_google_lang(target_lang)

    if src == tgt:
        result = []
        for seg in segments:
            result.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "translated": seg["text"],
            })
        return result

    t = GoogleTranslator(source=src, target=tgt)
    result = []
    for seg in segments:
        text = seg["text"]
        translated = t.translate(text) if text.strip() else ""
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "translated": translated,
        })
    return result
