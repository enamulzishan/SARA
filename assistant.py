import threading

try:
    from ai.brain import ask_ai
except ImportError:
    def ask_ai(text):
        return "I am processing your request."

import memory

try:
    from speech.stt import listen
except ImportError:
    def listen(timeout=8, phrase_time_limit=12, stop_event=None):
        return ""

try:
    from speech.tts import speak_smart, stop_speech
except ImportError:
    def speak_smart(text):
        pass
    def stop_speech():
        pass

_tts_muted = False
_listen_stop_event = threading.Event()

def set_tts_muted(muted):
    global _tts_muted
    _tts_muted = muted

def process_message(text):
    try:
        response = ask_ai(text)
    except Exception as e:
        response = f"I encountered an internal error while processing that: {str(e)}"
        
    if not _tts_muted:
        try:
            speak_smart(response)
        except Exception as e:
            print(f"TTS Error: {e}")
            
    return response

def record_audio_and_transcribe():
    _listen_stop_event.clear()
    try:
        stop_speech()
    except Exception:
        pass
        
    try:
        text = listen(timeout=8, phrase_time_limit=12, stop_event=_listen_stop_event)
    except Exception as e:
        print(f"STT Error: {e}")
        text = ""
    return text

def stop_listening():
    _listen_stop_event.set()

def get_history():
    return memory.get_recent_history()

def get_history_list():
    return memory.get_all_history_grouped()

def clear_history():
    memory.clear_history()

def get_facts():
    return memory.get_all_facts()

def delete_fact(key):
    memory.forget_fact(key)
    
def save_initial_facts(facts_dict):
    for k, v in facts_dict.items():
        memory._upsert_fact(k, str(v))
        
def new_session():
    return memory.start_new_session()