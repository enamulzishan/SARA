import threading

from speech.stt import listen
from speech.tts import speak_smart, stop_speech
from ai.brain import ask_ai

_stop_event = threading.Event()


def request_stop():
    """Signal the CLI voice loop to exit on the next check."""
    _stop_event.set()
    stop_speech()


def voice_mode(stop_event=None):
    event = stop_event or _stop_event
    event.clear()

    speak_smart("I'm listening...")

    while not event.is_set():
        command = listen(timeout=8, phrase_time_limit=12, stop_event=event)

        if event.is_set():
            break

        if not command:
            continue

        if "switch to chat" in command:
            speak_smart("Switching to chat mode.")
            return "chat"

        if "exit" in command:
            speak_smart("Goodbye!")
            exit()

        response = ask_ai(command)
        if event.is_set():
            break
        speak_smart(response)
