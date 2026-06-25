import json
import shutil
from pathlib import Path
from config import VOICES_DIR

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}


def get_available_engines() -> list[str]:
    engines = ["silero"]
    try:
        from TTS.tts.models.xtts import Xtts
        engines.append("xtts")
    except ImportError:
        pass
    return engines


def get_voice_profiles() -> list[dict]:
    voices = []

    voices.append({
        "id": "silero_xenia",
        "name": "Ксения (Silero)",
        "engine": "silero",
        "language": "ru",
        "model_id": "v4_ru",
        "speaker": "xenia",
        "gender": "female",
    })
    voices.append({
        "id": "silero_baya",
        "name": "Бая (Silero)",
        "engine": "silero",
        "language": "ru",
        "model_id": "v4_ru",
        "speaker": "baya",
        "gender": "female",
    })
    voices.append({
        "id": "silero_kseniya",
        "name": "Ксения (Silero 16kHz)",
        "engine": "silero",
        "language": "ru",
        "model_id": "v4_ru",
        "speaker": "kseniya",
        "gender": "female",
    })
    voices.append({
        "id": "silero_natasha",
        "name": "Наташа (Silero)",
        "engine": "silero",
        "language": "ru",
        "model_id": "v4_ru",
        "speaker": "natasha",
        "gender": "female",
    })
    voices.append({
        "id": "silero_aidar",
        "name": "Айдар (Silero)",
        "engine": "silero",
        "language": "ru",
        "model_id": "v4_ru",
        "speaker": "aidar",
        "gender": "male",
    })

    seen_ids = {v["id"] for v in voices}

    for path in VOICES_DIR.iterdir():
        if path.is_dir() and (path / "profile.json").exists():
            with open(path / "profile.json", encoding="utf-8") as f:
                profile = json.load(f)
            if profile["id"] not in seen_ids:
                voices.append(profile)
                seen_ids.add(profile["id"])

    for fpath in VOICES_DIR.iterdir():
        if fpath.is_file() and fpath.suffix.lower() in _AUDIO_EXTENSIONS:
            vid = fpath.stem
            if vid not in seen_ids:
                voices.append({
                    "id": vid,
                    "name": vid,
                    "engine": "xtts",
                    "language": "ru",
                    "sample_path": str(fpath),
                    "gender": "custom",
                })
                seen_ids.add(vid)

    return voices


def get_voice_by_id(voice_id: str) -> dict | None:
    for v in get_voice_profiles():
        if v["id"] == voice_id:
            return v
    return None


def clone_voice(name: str, audio_path: str | Path, language: str = "ru") -> dict:
    import torch
    from TTS.tts.models.xtts import Xtts

    voice_dir = VOICES_DIR / name.lower().replace(" ", "_")
    voice_dir.mkdir(exist_ok=True)

    sample_path = voice_dir / "sample.wav"
    shutil.copy2(str(audio_path), str(sample_path))

    model = Xtts.init_from_pretrained("tts_models/multilingual/multi-dataset/xtts_v2")
    model.to(torch.device("cpu"))

    profile = {
        "id": voice_dir.name,
        "name": name,
        "engine": "xtts",
        "language": language,
        "model_path": str(voice_dir),
        "sample_path": str(sample_path),
        "gender": "custom",
    }

    import json
    with open(voice_dir / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    return profile


def synthesize_xtts(text: str, voice_id: str, language: str = "ru") -> tuple:
    import torch
    from TTS.tts.models.xtts import Xtts

    profile = get_voice_by_id(voice_id)
    if profile is None:
        raise ValueError(f"Voice profile not found: {voice_id}")

    model = Xtts.init_from_pretrained("tts_models/multilingual/multi-dataset/xtts_v2")
    model.to(torch.device("cpu"))

    if language == "ru":
        lang = "ru"
    else:
        lang = "en"

    outputs = model.synthesize(
        text,
        config=model.config,
        speaker_wav=profile["sample_path"],
        language=lang,
    )

    audio = torch.tensor(outputs["wav"]).squeeze()
    return audio
