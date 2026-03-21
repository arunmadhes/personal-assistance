import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

# Download models on first run (only needs internet once)
# After that, fully offline
openwakeword.utils.download_models()

# Load the hey_jarvis model (or use "alexa", "hey_mycroft", etc.)
# You can also use a custom .tflite model path here
oww_model = Model(
    wakeword_models=["hey_jarvis"],  # built-in pre-trained model
    inference_framework="tflite"
)

SAMPLE_RATE = 16000
CHUNK_SIZE  = 1280  # 80ms at 16kHz — recommended by openWakeWord


def listen_for_wake_word():
    """
    Blocks until the wake word 'Hey Jarvis' is detected.
    Fully offline — no API key or internet required after first model download.
    """

    print("👂 Waiting for wake word ('Hey Jarvis')...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=CHUNK_SIZE,
    ) as stream:

        while True:
            audio_chunk, _ = stream.read(CHUNK_SIZE)

            # Convert to flat numpy int16 array
            audio_np = audio_chunk.flatten()

            # Get predictions
            predictions = oww_model.predict(audio_np)

            # Check if hey_jarvis confidence crosses threshold
            for model_name, score in predictions.items():
                if score >= 0.5:
                    print(f"✅ Wake word detected! ({model_name}: {score:.2f})")
                    oww_model.reset()  # reset state for next detection
                    return True