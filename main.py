import sys
import os
import json
import webview

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import assistant

class Api:
    def __init__(self):
        self.settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        self.settings = self._load_settings_file()
        assistant.set_tts_muted(self.settings.get("tts_muted", False))
        
    def _load_settings_file(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"theme": "light", "tts_muted": False}
        
    def _save_settings_file(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")
            
    def load_settings(self):
        return self.settings

    def save_theme(self, theme):
        self.settings["theme"] = theme
        self._save_settings_file()
        return True
        
    def set_tts_muted(self, muted):
        self.settings["tts_muted"] = muted
        self._save_settings_file()
        assistant.set_tts_muted(muted)
        return True
        
    def send_message(self, text):
        return assistant.process_message(text)
        
    def start_listening(self):
        return assistant.record_audio_and_transcribe()
        
    def stop_listening(self):
        assistant.stop_listening()
        return True
        
    def get_history(self):
        return assistant.get_history()
        
    def get_history_list(self):
        return assistant.get_history_list()
        
    def clear_history(self):
        assistant.clear_history()
        return True
        
    def get_facts(self):
        return assistant.get_facts()
        
    def delete_fact(self, key):
        assistant.delete_fact(key)
        return True
        
    def set_memory_enabled(self, enabled, initial_facts=None):
        self.settings["memory_enabled"] = enabled
        self._save_settings_file()
        if enabled and initial_facts:
            assistant.save_initial_facts(initial_facts)
        return True
        
    def new_session(self):
        return assistant.new_session()

if __name__ == "__main__":
    print("SARA Assistant Started...")
    api = Api()
    api.new_session()
    html_path = os.path.join(os.path.dirname(__file__), 'ui', 'index.html')
    webview.create_window(
        'SARA AI',
        url=f'file:///{html_path}',
        js_api=api,
        width=960,
        height=600,
        resizable=True
    )
    webview.start()