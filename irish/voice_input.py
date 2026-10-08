import json
import os
import queue
from pathlib import Path

import sounddevice as sd
from dotenv import load_dotenv
from vosk import KaldiRecognizer, Model


load_dotenv(dotenv_path=Path(__file__).parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "vosk-model-small-en-us-0.15"
MODEL_PATH = Path(os.getenv("VOSK_MODEL_PATH", str(DEFAULT_MODEL_PATH))).expanduser()

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Vosk model not found at '{MODEL_PATH}'. Set VOSK_MODEL_PATH in .env if needed."
    )

model = Model(str(MODEL_PATH))
q = queue.Queue()


def callback(indata, frames, time, status):
    if status:
        print("Voice input status:", status)
    q.put(bytes(indata))


def listen(timeout=10):
    samplerate = 16000
    rec = KaldiRecognizer(model, samplerate)

    print("Listening...")

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        while True:
            try:
                data = q.get(timeout=timeout)
            except queue.Empty:
                return ""

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print("You said:", text)
                    return text
