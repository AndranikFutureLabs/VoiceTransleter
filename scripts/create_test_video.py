import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEXT = "Hello everyone, this is a test video for voice translation. We are testing how well the translation system works."
OUTPUT = "temp/test_input.mp4"

def main():
    os.makedirs("temp", exist_ok=True)

    print("Generating English test audio via gTTS...")
    try:
        from gtts import gTTS
        tts = gTTS(text=TEXT, lang="en", slow=False)
        tts.save("temp/test_audio_en.mp3")
        print("  gTTS audio saved")
    except ImportError:
        print("  gTTS not installed, trying pip install...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gtts"], check=True)
        from gtts import gTTS
        tts = gTTS(text=TEXT, lang="en", slow=False)
        tts.save("temp/test_audio_en.mp3")
        print("  gTTS audio saved")

    print("Creating test video with blank screen + audio...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=8",
        "-i", "temp/test_audio_en.mp3",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(OUTPUT),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size = os.path.getsize(OUTPUT)
    print(f"Test video created: {OUTPUT} ({size} bytes)")
    print(f"\nRun pipeline: python main.py \"{OUTPUT}\"")

if __name__ == "__main__":
    main()
