import queue
import re
import threading
import time

import pyttsx3


CODE_RESPONSE_SUMMARY = (
    "I've generated a code example. Please check the chat window for the complete code."
)

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_CODE_HINT_RE = re.compile(
    r"^\s*(def |class |import |from |for |while |if |elif |else:|try:|except |"
    r"function |const |let |var |public |private |#include|SELECT |INSERT |UPDATE |"
    r"return |print\(|console\.log)",
    re.IGNORECASE | re.MULTILINE,
)


def _contains_code(text):
    if not text:
        return False

    if _CODE_FENCE_RE.search(text):
        return True

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) >= 4 and _CODE_HINT_RE.search(text):
        return True

    inline_code_count = len(_INLINE_CODE_RE.findall(text))
    return inline_code_count >= 3


def speech_text_for_response(text):
    """Return the short, voice-friendly version of an assistant response."""
    if not text:
        return ""

    if _contains_code(text):
        return CODE_RESPONSE_SUMMARY
    return str(text).strip()


class _SpeechController:
    def __init__(self):
        self._requests = queue.Queue()
        self._state_lock = threading.Lock()
        self._engine = None
        self._generation = 0
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def speak(self, text, *, smart=True, on_start=None, on_done=None, on_error=None):
        spoken_text = speech_text_for_response(text)
        if not spoken_text:
            return

        with self._state_lock:
            self._generation += 1
            generation = self._generation
            engine = self._engine

        self._drain_pending()
        self._stop_engine(engine)
        self._requests.put((generation, spoken_text, smart, on_start, on_done, on_error))

    def stop(self):
        with self._state_lock:
            self._generation += 1
            engine = self._engine
        self._drain_pending()
        self._stop_engine(engine)

    def _drain_pending(self):
        while True:
            try:
                self._requests.get_nowait()
                self._requests.task_done()
            except queue.Empty:
                return

    def _stop_engine(self, engine):
        if engine is None:
            return
        try:
            engine.stop()
        except Exception:
            pass
        try:
            engine.endLoop()
        except Exception:
            pass

    def _worker(self):
        engine = self._init_engine()
        with self._state_lock:
            self._engine = engine

        while True:
            generation, text, smart, on_start, on_done, on_error = self._requests.get()
            is_current = lambda: self._is_current(generation)

            try:
                if not is_current():
                    continue

                if on_start:
                    on_start()

                if engine is not None:
                    self._say(engine, text, smart, is_current)

                if is_current() and on_done:
                    on_done()
            except Exception as exc:
                print(f"[TTS error] {exc}")
                if is_current() and on_error:
                    try:
                        on_error(exc)
                    except Exception:
                        pass
            finally:
                self._requests.task_done()

    def _is_current(self, generation):
        with self._state_lock:
            return generation == self._generation

    def _init_engine(self):
        try:
            engine = pyttsx3.init()
            self._choose_voice(engine)
            engine.setProperty("rate", 168)
            engine.setProperty("volume", 1.0)
            return engine
        except Exception as exc:
            print(f"[TTS disabled] {exc}")
            return None

    def _choose_voice(self, engine):
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return

        preferred = (
            "natural",
            "aria",
            "jenny",
            "zira",
            "susan",
            "hazel",
            "female",
        )
        for voice in voices:
            name = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
            if any(token in name for token in preferred):
                engine.setProperty("voice", voice.id)
                return

    def _say(self, engine, text, smart, is_current):
        parts = self._split_for_speech(text) if smart else [text]
        for part in parts:
            if not is_current():
                break
            engine.say(part)
            engine.runAndWait()
            if smart and is_current():
                time.sleep(0.2)

    def _split_for_speech(self, text):
        cleaned = re.sub(r"\s+", " ", text).strip()
        return [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", cleaned)
            if part.strip()
        ]


_controller = _SpeechController()


def speak(text):
    """Speak text, interrupting any current speech."""
    _controller.speak(text, smart=False)


def speak_smart(text):
    """Speak text with natural pauses, interrupting any current speech."""
    _controller.speak(text, smart=True)


def speak_response(text, on_start=None, on_done=None, on_error=None):
    """Speak an assistant response with GUI-friendly lifecycle callbacks."""
    _controller.speak(
        text,
        smart=True,
        on_start=on_start,
        on_done=on_done,
        on_error=on_error,
    )


def stop_speech():
    _controller.stop()
