import subprocess
from pathlib import Path
from config import TEMP_DIR, WHISPER_SAMPLE_RATE


def extract_audio(video_path: str | Path, output_path: str | Path | None = None) -> Path:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        output_path = TEMP_DIR / f"{video_path.stem}_audio.wav"

    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(WHISPER_SAMPLE_RATE),
        "-ac", "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def get_video_duration(video_path: str | Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())
