from modes.voice_mode import voice_mode
from modes.chat_mode import chat_mode

def run_assistant():
    mode = "voice"

    while True:
        if mode == "voice":
            mode = voice_mode()
        else:
            mode = chat_mode()