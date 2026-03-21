import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer


model = Model(r"C:\Users\arun1\OneDrive\Desktop\personal assistant\irish\vosk-model-small-en-us-0.15")

q = queue.Queue()


def callback(indata, frames, time, status):
    q.put(bytes(indata))


def listen():

    samplerate = 16000

    rec = KaldiRecognizer(model, samplerate)

    print("🎤 Listening...")

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback
    ):

        while True:

            data = q.get()

            if rec.AcceptWaveform(data):

                result = json.loads(rec.Result())

                text = result.get("text", "")

                if text:
                    print("You said:", text)
                    return text