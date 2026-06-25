from faster_whisper import WhisperModel
from config import WHISPER_MODEL, DEVICE, COMPUTE_TYPE


_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def transcribe(audio_path: str, language: str = "en") -> list[dict]:
    model = get_model()
    segments, info = model.transcribe(audio_path, language=language, beam_size=5)

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
    return result
