import queue
import threading
import pyttsx3

speech_queue = queue.Queue()
engine = None
engine_lock = threading.Lock()


def _get_engine():
    global engine

    if engine is not None:
        return engine

    with engine_lock:
        if engine is None:
            try:
                engine = pyttsx3.init()
            except Exception:
                engine = False

    return engine if engine is not False else None


def speaker():

    while True:
        text = speech_queue.get()

        if text is None:
            break

        current_engine = _get_engine()
        if not current_engine:
            continue

        try:
            current_engine.say(text)
            current_engine.runAndWait()
        except Exception:
            continue


threading.Thread(target=speaker, daemon=True).start()


def speak(token):
    speech_queue.put(token)
