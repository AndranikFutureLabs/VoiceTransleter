import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
MODELS_DIR = BASE_DIR / "models"
VOICES_DIR = BASE_DIR / "voices"

TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
VOICES_DIR.mkdir(exist_ok=True)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
DEVICE = os.getenv("DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")

SILERO_LANGUAGE = "ru"
SILERO_MODEL_ID = "v4_ru"
SILERO_SPEAKER = "xenia"

TRANSLATE_SOURCE = "en"
TRANSLATE_TARGET = "ru"
TRANSLATOR_BACKEND = os.getenv("TRANSLATOR_BACKEND", "google")

WHISPER_SAMPLE_RATE = 16000
TTS_SAMPLE_RATE = 24000
OUTPUT_SAMPLE_RATE = 48000
