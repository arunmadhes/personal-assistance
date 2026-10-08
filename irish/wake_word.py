import importlib.util
import os
from pathlib import Path

import openwakeword
import sounddevice as sd
from dotenv import load_dotenv
from openwakeword.model import Model


load_dotenv(dotenv_path=Path(__file__).parent / ".env")

WAKEWORD_NAME = os.getenv("WAKEWORD_NAME", "hey_jarvis")
WAKEWORD_THRESHOLD = float(os.getenv("WAKEWORD_THRESHOLD", "0.5"))
WAKEWORD_AUTO_DOWNLOAD = os.getenv("WAKEWORD_AUTO_DOWNLOAD", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}
WAKEWORD_FRAMEWORK = os.getenv("WAKEWORD_FRAMEWORK", "auto").strip().lower()

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280

_oww_model = None


def _module_available(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def _resolve_inference_framework():
    if WAKEWORD_FRAMEWORK in {"tflite", "onnx"}:
        return WAKEWORD_FRAMEWORK

    if _module_available("tflite_runtime.interpreter"):
        return "tflite"

    if _module_available("onnxruntime"):
        return "onnx"

    raise RuntimeError(
        "No supported wake-word inference runtime is installed. "
        "Install `tflite-runtime` or `onnxruntime`, or set WAKEWORD_FRAMEWORK explicitly."
    )


def _get_wake_word_model():
    global _oww_model

    if _oww_model is not None:
        return _oww_model

    if WAKEWORD_AUTO_DOWNLOAD:
        openwakeword.utils.download_models()

    _oww_model = Model(
        wakeword_models=[WAKEWORD_NAME],
        inference_framework=_resolve_inference_framework(),
    )
    return _oww_model


def listen_for_wake_word():
    print(f"Waiting for wake word ('{WAKEWORD_NAME}')...")
    model = _get_wake_word_model()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=CHUNK_SIZE,
    ) as stream:
        while True:
            audio_chunk, _ = stream.read(CHUNK_SIZE)
            audio_np = audio_chunk.flatten()
            predictions = model.predict(audio_np)

            for model_name, score in predictions.items():
                if score >= WAKEWORD_THRESHOLD:
                    print(f"Wake word detected! ({model_name}: {score:.2f})")
                    model.reset()
                    return True
