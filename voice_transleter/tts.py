import os

# Add bundled FFmpeg to PATH and DLL search path (torchcodec needs DLLs)
_ffmpeg_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
if os.path.isdir(_ffmpeg_bin):
    os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_ffmpeg_bin)

import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from silero import silero_tts
from config import TEMP_DIR, TTS_SAMPLE_RATE


_silero_model = None
_silero_utils = None
_xtts_model = None


def _get_silero():
    global _silero_model, _silero_utils
    if _silero_model is None:
        _silero_model, _silero_utils = silero_tts(language="ru", speaker="v4_ru")
        _silero_model.to(torch.device("cpu"))
    return _silero_model


def _get_xtts():
    global _xtts_model
    if _xtts_model is None:
        # Ensure bundled FFmpeg DLLs are findable by torchcodec
        _ffmpeg_bin = str(Path(__file__).parent.parent / "bin")
        if os.path.isdir(_ffmpeg_bin):
            os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
        os.environ["COQUI_TOS_AGREED"] = "1"
        from TTS.api import TTS
        # PyTorch 2.6 compat: TTS 0.22.0 uses torch.load without weights_only
        import torch as _torch
        _original_load = _torch.load
        def _patched_load(f, *a, **kw):
            kw.setdefault('weights_only', False)
            return _original_load(f, *a, **kw)
        _torch.load = _patched_load
        try:
            tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
            _xtts_model = tts.synthesizer.tts_model
            _xtts_model.to(torch.device("cpu"))
        finally:
            _torch.load = _original_load
    return _xtts_model


_xtts_download_tried = False


def _get_tts_cache_dirs() -> list[Path]:
    if os.name == 'nt':
        return [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'tts' / 'tts_models--multilingual--multi-dataset--xtts_v2',
            Path(os.environ.get('APPDATA', '')) / 'tts' / 'tts_models' / 'multilingual' / 'multi-dataset' / 'xtts_v2',
        ]
    return [
        Path.home() / '.local' / 'share' / 'tts' / 'tts_models' / 'multilingual' / 'multi-dataset' / 'xtts_v2',
    ]


def is_xtts_downloaded() -> bool:
    # Check known cache paths
    for cache_dir in _get_tts_cache_dirs():
        if not cache_dir.exists():
            continue
        model_files = list(cache_dir.rglob('*.pth'))
        if model_files and any(f.stat().st_size > 500_000_000 for f in model_files):
            return True
    # Broader search under all tts cache roots
    if os.name == 'nt':
        roots = [Path(os.environ.get('LOCALAPPDATA', '')), Path(os.environ.get('APPDATA', ''))]
    else:
        roots = [Path.home() / '.local' / 'share']
    for root in roots:
        for d in root.rglob('*xtts_v2*'):
            if d.is_dir():
                model_files = list(d.rglob('*.pth'))
                if model_files and any(f.stat().st_size > 500_000_000 for f in model_files):
                    return True
    return False


def download_xtts(progress_callback=None):
    global _xtts_model, _xtts_download_tried
    # Ensure bundled FFmpeg DLLs are findable by torchcodec
    _ffmpeg_bin = str(Path(__file__).parent.parent / "bin")
    if os.path.isdir(_ffmpeg_bin):
        os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
    os.environ["COQUI_TOS_AGREED"] = "1"
    import torch as _torch
    _original_load = _torch.load
    def _patched_load(f, *a, **kw):
        kw.setdefault('weights_only', False)
        return _original_load(f, *a, **kw)
    _torch.load = _patched_load
    try:
        from TTS.api import TTS
        if progress_callback:
            progress_callback("Загрузка модели XTTS v2 (~1.87 ГБ)...")
            progress_callback("Следите за прогрессом в консоли. Не закрывайте окно до завершения!")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        _xtts_model = tts.synthesizer.tts_model
        _xtts_model.to(torch.device("cpu"))
        _xtts_download_tried = True
        if progress_callback:
            progress_callback("XTTS v2 загружена и готова к использованию!")
    finally:
        _torch.load = _original_load


def synthesize_text(text: str, voice_profile: dict) -> torch.Tensor:
    engine = voice_profile.get("engine", "silero")

    if engine == "silero":
        model = _get_silero()
        speaker = voice_profile.get("speaker", "xenia")
        audio = model.apply_tts(text=text, speaker=speaker, sample_rate=TTS_SAMPLE_RATE)
        return audio

    elif engine == "xtts":
        model = _get_xtts()
        sample_path = voice_profile.get("sample_path")
        lang = voice_profile.get("language", "ru")
        outputs = model.synthesize(
            text,
            config=model.config,
            speaker_wav=str(sample_path),
            language=lang,
        )
        audio = torch.tensor(outputs["wav"]).squeeze()
        return audio

    else:
        raise ValueError(f"Unknown TTS engine: {engine}")


def synthesize_segments(segments: list[dict], voice_profile: dict) -> list[dict]:
    result = []
    for seg in segments:
        audio = synthesize_text(seg["translated"], voice_profile)
        seg_path = TEMP_DIR / f"seg_{seg['start']:.2f}.wav"
        if audio.dim() == 1:
            sf.write(str(seg_path), audio.numpy(), TTS_SAMPLE_RATE)
        else:
            sf.write(str(seg_path), audio.cpu().numpy(), TTS_SAMPLE_RATE)
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "original": seg["text"],
            "translated": seg["translated"],
            "audio_path": str(seg_path),
        })
    return result
