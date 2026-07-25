import os
import sys
import json

from dotenv import load_dotenv

load_dotenv()

def _get_setting_with_fallback(key, env_var, default=""):
    val = os.getenv(env_var, "").strip() if env_var else ""
    if not val:
        settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = str(data.get(key, "")).strip()
            except Exception:
                pass
    return val or default

LLM_PROVIDER = _get_setting_with_fallback("llm_provider", "LLM_PROVIDER", "groq").lower()

GROQ_API_KEY = _get_setting_with_fallback("groq_api_key", "GROQ_API_KEY", "")
GROQ_MODEL = _get_setting_with_fallback("groq_model", "GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_API_KEY = _get_setting_with_fallback("gemini_api_key", "GEMINI_API_KEY", "")
GEMINI_MODEL = _get_setting_with_fallback("gemini_model", "GEMINI_MODEL", "gemini-2.5-flash")

OPENROUTER_API_KEY = _get_setting_with_fallback("openrouter_api_key", "OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = _get_setting_with_fallback("openrouter_model", "OPENROUTER_MODEL", "openrouter/auto")

# Backwards compatibility aliases
API_KEY = GROQ_API_KEY
MODEL = GROQ_MODEL

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()
SERPAPI_ENGINE = os.getenv("SERPAPI_ENGINE", "google").strip()
SERPAPI_SEARCH_ALWAYS = os.getenv("SERPAPI_SEARCH_ALWAYS", "false").strip().lower() in ("1", "true", "yes", "y")
WAKE_WORD = os.getenv("WAKE_WORD", "hey sara").strip().lower()
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "voice").strip().lower()


def validate_config():
    """Return an error message when required configuration is missing."""
    provider = LLM_PROVIDER
    if provider == "groq" and not GROQ_API_KEY:
        return (
            "GROQ_API_KEY is missing or empty. "
            "Add it to your .env file: GROQ_API_KEY=your_key_here"
        )
    elif provider == "gemini" and not GEMINI_API_KEY:
        return (
            "GEMINI_API_KEY is missing or empty. "
            "Add it to your .env file: GEMINI_API_KEY=your_key_here"
        )
    elif provider == "openrouter" and not OPENROUTER_API_KEY:
        return (
            "OPENROUTER_API_KEY is missing or empty. "
            "Add it to your .env file: OPENROUTER_API_KEY=your_key_here"
        )
    return None


_config_error = validate_config()
if _config_error and __name__ == "__main__":
    sys.exit(_config_error)
