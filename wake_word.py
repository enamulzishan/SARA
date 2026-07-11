from speech.stt import listen
from config import WAKE_WORD


def wait_for_wake_word(stop_event=None):
    print("🟡 Waiting for wake word...")

    while True:
        if stop_event and stop_event.is_set():
            return False

        text = listen(timeout=3, phrase_time_limit=8, stop_event=stop_event)

        if stop_event and stop_event.is_set():
            return False

        if text and WAKE_WORD in text:
            print("🟢 Wake word detected!")
            return True
