import os
import sys
import time
import logging
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Mute noisy logs during diagnostics
logging.getLogger("sara.ai").setLevel(logging.CRITICAL)

import config
from ai.brain import GroqProvider, GeminiProvider, OpenRouterProvider


def check_provider(name: str, provider_cls, api_key: str, model: str) -> Dict[str, Any]:
    if not api_key or not str(api_key).strip():
        return {
            "provider": name,
            "status": "Not configured",
            "detail": "key missing in .env",
            "success": False,
            "icon": "⚠️",
        }

    provider = provider_cls(api_key=str(api_key).strip(), model=model)
    messages = [{"role": "user", "content": "Say hello in one word."}]

    start_time = time.time()
    try:
        reply = provider.generate(messages, stream=False, timeout=15)
        elapsed = time.time() - start_time
        return {
            "provider": name,
            "status": "OK",
            "detail": f"responded in {elapsed:.1f}s",
            "success": True,
            "icon": "✅",
        }
    except Exception as exc:
        err_str = str(exc).lower()
        err_type = type(exc).__name__.lower()
        full_err = f"{err_str} {err_type}"

        if any(w in full_err for w in ["401", "403", "unauthorized", "authentication", "access denied", "api_key_invalid", "permissiondenied", "invalid api key", "invalid_api_key"]):
            detail = "401/403 Unauthorized (check API key)"
        elif any(w in full_err for w in ["429", "rate-limiting", "rate limit", "resourceexhausted", "quota"]):
            detail = "429 Rate limit hit (please wait or check quota)"
        elif any(w in full_err for w in ["timed out", "connection", "could not connect", "network", "timeout"]):
            detail = "Network/Timeout error (check internet connection)"
        else:
            detail = f"Error: {str(exc)[:120]}"

        return {
            "provider": name,
            "status": "FAILED",
            "detail": detail,
            "success": False,
            "icon": "❌",
        }


def check_serpapi(api_key: str) -> Dict[str, Any]:
    if not api_key or not str(api_key).strip():
        return {
            "provider": "SerpAPI",
            "status": "Not configured",
            "detail": "key missing in .env",
            "success": False,
            "icon": "⚠️",
        }

    start_time = time.time()
    try:
        url = "https://serpapi.com/search"
        response = requests.get(
            url,
            params={
                "q": "test",
                "engine": getattr(config, "SERPAPI_ENGINE", "google"),
                "api_key": str(api_key).strip(),
                "num": 1,
            },
            timeout=10,
        )
        elapsed = time.time() - start_time

        if response.status_code in (401, 403) or (response.status_code == 400 and "invalid api" in response.text.lower()) or "invalid api key" in response.text.lower() or "unauthorized" in response.text.lower():
            return {
                "provider": "SerpAPI",
                "status": "FAILED",
                "detail": "401 Unauthorized (check API key)",
                "success": False,
                "icon": "❌",
            }
        elif response.status_code == 429 or "rate limit" in response.text.lower() or "too many requests" in response.text.lower() or "exhausted" in response.text.lower() or "out of searches" in response.text.lower() or "exceeded" in response.text.lower():
            return {
                "provider": "SerpAPI",
                "status": "FAILED",
                "detail": "429 Rate limit exceeded",
                "success": False,
                "icon": "❌",
            }
        elif not response.ok:
            return {
                "provider": "SerpAPI",
                "status": "FAILED",
                "detail": f"Error (HTTP {response.status_code})",
                "success": False,
                "icon": "❌",
            }

        data = response.json()
        if "error" in data:
            err_msg = str(data["error"]).lower()
            if "api_key" in err_msg or "unauthorized" in err_msg or "invalid" in err_msg or "key" in err_msg:
                detail = "401 Unauthorized (check API key)"
            elif "rate" in err_msg or "exhausted" in err_msg or "limit" in err_msg or "exceeded" in err_msg or "searches" in err_msg:
                detail = "429 Rate limit exceeded"
            else:
                detail = f"Error: {data['error'][:100]}"
            return {
                "provider": "SerpAPI",
                "status": "FAILED",
                "detail": detail,
                "success": False,
                "icon": "❌",
            }

        return {
            "provider": "SerpAPI",
            "status": "OK",
            "detail": f"responded in {elapsed:.1f}s",
            "success": True,
            "icon": "✅",
        }
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
        return {
            "provider": "SerpAPI",
            "status": "FAILED",
            "detail": "network/timeout error",
            "success": False,
            "icon": "❌",
        }
    except Exception as exc:
        err_str = str(exc).lower()
        if any(w in err_str for w in ["401", "403", "unauthorized", "api_key", "key"]):
            detail = "401 Unauthorized (check API key)"
        elif any(w in err_str for w in ["429", "rate", "limit", "exhausted", "exceeded"]):
            detail = "429 Rate limit exceeded"
        elif any(w in err_str for w in ["timed out", "connection", "network", "timeout"]):
            detail = "network/timeout error"
        else:
            detail = f"Error: {str(exc)[:100]}"
        return {
            "provider": "SerpAPI",
            "status": "FAILED",
            "detail": detail,
            "success": False,
            "icon": "❌",
        }


def run_diagnostics() -> List[Dict[str, Any]]:
    # Reload .env in case it was modified on disk since app start
    load_dotenv(override=True)

    groq_key = config._get_setting_with_fallback("groq_api_key", "GROQ_API_KEY", "")
    gemini_key = config._get_setting_with_fallback("gemini_api_key", "GEMINI_API_KEY", "")
    or_key = config._get_setting_with_fallback("openrouter_api_key", "OPENROUTER_API_KEY", "")
    serpapi_key = config._get_setting_with_fallback("serpapi_api_key", "SERPAPI_API_KEY", "") or os.getenv("SERPAPI_KEY", "").strip() or config._get_setting_with_fallback("serpapi_key", "SERPAPI_KEY", "")

    results = [
        check_provider("Groq", GroqProvider, groq_key, config.GROQ_MODEL),
        check_provider("Gemini", GeminiProvider, gemini_key, config.GEMINI_MODEL),
        check_provider("OpenRouter", OpenRouterProvider, or_key, config.OPENROUTER_MODEL),
        check_serpapi(serpapi_key),
    ]
    return results


def main():
    print("\n--- LLM Provider API Key Diagnostics ---")
    results = run_diagnostics()
    for res in results:
        print(f"{res['icon']} {res['provider']}: {res['status']} — {res['detail']}")
    print("----------------------------------------\n")


if __name__ == "__main__":
    main()
