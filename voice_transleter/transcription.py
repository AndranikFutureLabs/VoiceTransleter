from faster_whisper import WhisperModel
from config import WHISPER_MODEL, DEVICE, COMPUTE_TYPE

LANG_NAMES = {
    "en": "Английский", "es": "Испанский", "fr": "Французский",
    "de": "Немецкий", "it": "Итальянский", "pt": "Португальский",
    "nl": "Нидерландский", "pl": "Польский", "ru": "Русский",
    "zh": "Китайский", "ja": "Японский", "ko": "Корейский",
    "ar": "Арабский", "tr": "Турецкий", "hi": "Хинди",
    "vi": "Вьетнамский", "th": "Тайский", "uk": "Украинский",
    "sv": "Шведский", "da": "Датский", "fi": "Финский",
    "cs": "Чешский", "ro": "Румынский", "hu": "Венгерский",
    "el": "Греческий", "he": "Иврит", "id": "Индонезийский",
    "ms": "Малайский", "no": "Норвежский", "sk": "Словацкий",
    "bg": "Болгарский", "sr": "Сербский", "hr": "Хорватский",
    "ca": "Каталанский", "lt": "Литовский", "lv": "Латышский",
    "et": "Эстонский", "sl": "Словенский",
}

_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def transcribe(audio_path: str, language: str = "auto") -> tuple[list[dict], str]:
    model = get_model()
    lang = None if language == "auto" else language
    segments, info = model.transcribe(audio_path, language=lang, beam_size=5)

    detected = info.language if lang is None else lang

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
    return result, detected
