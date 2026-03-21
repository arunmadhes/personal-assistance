import pyttsx3
import queue
import threading

engine = pyttsx3.init()

speech_queue = queue.Queue()


def speaker():

    while True:
        text = speech_queue.get()

        if text is None:
            break

        engine.say(text)
        engine.runAndWait()


threading.Thread(target=speaker, daemon=True).start()


def speak(token):
    speech_queue.put(token)