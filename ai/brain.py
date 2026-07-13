import datetime
import requests
import json

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

import memory

def _rollback_last_user_message():
    # If the request fails, we might want to delete the user message from DB.
    # For now, we won't strictly rollback DB messages to keep a true record,
    # or we can implement memory.delete_last_user_message() if strictly needed.
    pass


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
        return "[System Note: I couldn't reach the search service right now to get the latest info.]"

    if not response.ok:
        print(f"[SerpAPI] request returned status {response.status_code}: {response.text[:200]}")
        return "[System Note: The search service is currently returning errors.]"

    try:
        data = response.json()
    except ValueError:
        print("[SerpAPI] invalid JSON response")
        return "[System Note: The search service returned invalid data.]"

    return _format_serp_results(data)


def ask_ai(message):
    memory.save_message("user", message)

    search_context = None
    if _should_search(message):
        search_context = _search_serpapi(message)

    # Inject facts
    facts = memory.get_all_facts()
    facts_str = "{}"
    if facts:
        facts_str = json.dumps(facts, indent=2)
        
    recent_history = memory.get_recent_history(limit=10)
    history_str = "None"
    if recent_history:
        history_lines = [f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history]
        history_str = "\n".join(history_lines)
        
    system_content = f"""You are SARA, a personal AI assistant. Your identity: "I'm SARA, your AI assistant. I help with coding, research, productivity, learning, and everyday tasks. My goal is to provide accurate, practical, and easy-to-understand assistance while respecting your privacy and preferences."
Core behavior:

Be professional but friendly — natural, not robotic, not overly casual.
Never invent facts. If unsure or unverifiable, say so plainly and suggest checking a reliable source or searching the web.
Adapt tone: professional for work/coding, formal for research/academic topics, friendly for casual chat.
Stay context-aware — use the recent conversation history and known facts provided to understand follow-ups without asking the user to repeat themselves.
Prioritize solving the problem first, then explain — don't bury the answer under preamble.
Stay calm, patient, and respectful always — never sarcastic, argumentative, or emotional.
For technical/educational topics, explain concepts and best practices, not just the raw answer — help the user learn.
Keep simple answers short and direct; give detailed explanations only when the question needs it.
If a tool/API error occurs, explain clearly what went wrong and suggest a next step — never fail silently or crash the conversation.

Known facts about the user: {facts_str}
Recent conversation context: {history_str}"""
    
    if search_context:
        system_content += (
            "\n\nUse the search results below to answer the user. "
            "If the information is not directly available in the search results, say so and avoid guessing.\n\n"
            "Search results:\n" + search_context
        )
    
    # We pass the recent history in the system prompt as requested, so the actual messages payload only needs the system prompt and the latest user message
    messages = [{"role": "system", "content": system_content}, {"role": "user", "content": message}]

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

    memory.save_message("assistant", reply)
    memory.extract_and_save_facts(message, reply)
    return reply
