import time

import speech_recognition as sr

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
_ambient_calibrated = False


def listen(timeout=8, phrase_time_limit=12, stop_event=None):
    """Capture speech from the microphone with bounded wait times.

    If *stop_event* is set while listening, returns immediately with "".
    """
    global _ambient_calibrated

    if stop_event and stop_event.is_set():
        return ""

    with sr.Microphone() as source:
        print("🎤 Listening...")
        if not _ambient_calibrated:
            if stop_event and stop_event.is_set():
                return ""
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            _ambient_calibrated = True

        if stop_event and stop_event.is_set():
            return ""

        deadline = time.monotonic() + timeout
        audio = None

        while time.monotonic() < deadline:
            if stop_event and stop_event.is_set():
                return ""

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            chunk_timeout = min(0.5, remaining)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=chunk_timeout,
                    phrase_time_limit=phrase_time_limit,
                )
                break
            except sr.WaitTimeoutError:
                continue

        if audio is None:
            return ""

    try:
        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.strip().lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        print(f"[STT error] {exc}")
        return ""
