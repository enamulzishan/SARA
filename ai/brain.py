import datetime
import requests

from config import (
    API_KEY,
    MODEL,
    SERPAPI_API_KEY,
    SERPAPI_ENGINE,
    SERPAPI_SEARCH_ALWAYS,
)

API_URL = "https://api.groq.com/openai/v1/chat/completions"
SERPAPI_URL = "https://serpapi.com/search"
API_TIMEOUT = 30

history = []


def _rollback_last_user_message():
    if history and history[-1].get("role") == "user":
        history.pop()


def _friendly_http_error(status_code):
    if status_code == 401:
        return "Authentication failed. Please check your API key in the .env file."
    if status_code == 403:
        return "Access denied by the AI service. Please verify your API key permissions."
    if status_code == 429:
        return "The AI service is rate-limiting requests. Please wait a moment and try again."
    if status_code >= 500:
        return "The AI service is temporarily unavailable. Please try again later."
    return f"The AI service returned an error (HTTP {status_code}). Please try again."


def _is_datetime_query(message):
    lower = message.lower()
    datetime_terms = [
        "today",
        "today's date",
        "current date",
        "what is the date",
        "what is today's date",
        "date today",
        "current time",
        "time now",
        "what time is it",
    ]
    return any(term in lower for term in datetime_terms)


def _should_search(message):
    if not SERPAPI_API_KEY:
        return False
    if SERPAPI_SEARCH_ALWAYS:
        return True

    lower = message.lower()
    if "today" in lower or "current" in lower or "now" in lower:
        return True

    triggers = [
        "latest",
        "news",
        "weather",
        "stock",
        "price",
        "exchange rate",
        "live",
        "recent",
        "update",
        "real time",
        "who is",
        "what is",
        "when is",
        "where is",
        "did",
        "does",
        "is",
        "are",
        "can",
    ]
    return any(trigger in lower for trigger in triggers)


def _format_serp_results(data):
    parts = []

    if data.get("search_information"):
        info = data["search_information"]
        total = info.get("total_results")
        time_taken = info.get("search_time")
        if total is not None or time_taken is not None:
            summary = "Search information:"
            if total is not None:
                summary += f" {total} results"
            if time_taken is not None:
                summary += f" in {time_taken:.2f}s"
            parts.append(summary)

    if data.get("answer_box"):
        answer_box = data["answer_box"]
        answer = answer_box.get("answer") or answer_box.get("snippet")
        if answer:
            parts.append("Featured answer:\n" + answer)

    if data.get("organic_results"):
        for item in data["organic_results"][:5]:
            title = item.get("title") or "(no title)"
            link = item.get("link") or item.get("displayed_link") or ""
            snippet = item.get("snippet") or item.get("snippet_highlighted") or ""
            parts.append(f"{title}\n{link}\n{snippet}")

    if not parts and data.get("news_results"):
        for item in data["news_results"][:5]:
            title = item.get("title") or "(no title)"
            link = item.get("link") or ""
            source = item.get("source") or ""
            snippet = item.get("snippet") or ""
            parts.append(f"{title} ({source})\n{link}\n{snippet}")

    if not parts and data.get("inline_hashtag_results"):
        for item in data["inline_hashtag_results"][:5]:
            parts.append(item.get("name", "#unknown"))

    return "\n\n".join(parts).strip()


def _search_serpapi(query):
    if not SERPAPI_API_KEY:
        print("[SerpAPI] API key missing: skipping live search.")
        return None

    print(f"[SerpAPI] querying: {query}")
    try:
        response = requests.get(
            SERPAPI_URL,
            params={
                "q": query,
                "engine": SERPAPI_ENGINE,
                "api_key": SERPAPI_API_KEY,
                "num": 5,
            },
            timeout=API_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        print(f"[SerpAPI] request failed: {exc}")
        return None

    if not response.ok:
        print(f"[SerpAPI] request returned status {response.status_code}: {response.text[:200]}")
        return None

    try:
        data = response.json()
    except ValueError:
        print("[SerpAPI] invalid JSON response")
        return None

    return _format_serp_results(data)


def ask_ai(message):
    history.append({"role": "user", "content": message})

    if _is_datetime_query(message):
        today = datetime.datetime.now().strftime("%d %B %Y")
        response = f"Today's date is {today}."
        history.append({"role": "assistant", "content": response})
        return response

    search_context = None
    if _should_search(message):
        search_context = _search_serpapi(message)

    messages = history[-10:]
    if search_context:
        messages = [
            {
                "role": "system",
                "content": (
                    "Use the search results below to answer the user. "
                    "If the information is not directly available in the search results, say so and avoid guessing.\n\n"
                    "Search results:\n" + search_context
                ),
            }
        ] + messages

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        res = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=API_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        _rollback_last_user_message()
        return "The request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        _rollback_last_user_message()
        return "Could not connect to the AI service. Check your internet connection."
    except requests.exceptions.RequestException as exc:
        _rollback_last_user_message()
        return f"Network error while contacting the AI service: {exc}"

    if not res.ok:
        _rollback_last_user_message()
        return _friendly_http_error(res.status_code)

    try:
        data = res.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("missing choices")

        reply = choices[0].get("message", {}).get("content")
        if not reply or not str(reply).strip():
            raise ValueError("empty reply")
    except (ValueError, TypeError, KeyError, IndexError):
        _rollback_last_user_message()
        return "I received an invalid response from the AI service. Please try again."

    history.append({"role": "assistant", "content": reply})
    return reply
