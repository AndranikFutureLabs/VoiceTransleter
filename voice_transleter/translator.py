from deep_translator import GoogleTranslator
from config import TRANSLATE_SOURCE, TRANSLATE_TARGET


_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source=TRANSLATE_SOURCE, target=TRANSLATE_TARGET)
    return _translator


def translate_text(text: str) -> str:
    if not text.strip():
        return ""
    t = _get_translator()
    return t.translate(text)


def translate_segments(segments: list[dict]) -> list[dict]:
    result = []
    for seg in segments:
        translated = translate_text(seg["text"])
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "translated": translated,
        })
    return result
