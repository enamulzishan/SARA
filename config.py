import os
import sys

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "").strip()
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()
SERPAPI_ENGINE = os.getenv("SERPAPI_ENGINE", "google").strip()
SERPAPI_SEARCH_ALWAYS = os.getenv("SERPAPI_SEARCH_ALWAYS", "false").strip().lower() in ("1", "true", "yes", "y")
WAKE_WORD = os.getenv("WAKE_WORD", "hey sara").strip().lower()
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "voice").strip().lower()


def validate_config():
    """Return an error message when required configuration is missing."""
    if not API_KEY:
        return (
            "GROQ_API_KEY is missing or empty. "
            "Add it to your .env file: GROQ_API_KEY=your_key_here"
        )
    return None


_config_error = validate_config()
if _config_error:
    sys.exit(_config_error)
