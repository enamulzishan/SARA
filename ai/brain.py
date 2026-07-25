import datetime
import datetime
import requests
import json
import logging
from abc import ABC, abstractmethod
from typing import Union, Generator, List, Dict, Any, Optional

from config import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    GROQ_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    SERPAPI_API_KEY,
    SERPAPI_ENGINE,
    SERPAPI_SEARCH_ALWAYS,
)

API_URL = "https://api.groq.com/openai/v1/chat/completions"
SERPAPI_URL = "https://serpapi.com/search"
API_TIMEOUT = 30

import memory

logger = logging.getLogger("sara.ai")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMProvider(ABC):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(self, messages: List[Dict[str, Any]], stream: bool = False, images: Optional[List[Any]] = None, **kwargs) -> Union[str, Generator]:
        """Generate a completion from the LLM provider."""
        pass


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        super().__init__(api_key=api_key or GROQ_API_KEY, model=model or GROQ_MODEL)

    def generate(self, messages: List[Dict[str, Any]], stream: bool = False, images: Optional[List[Any]] = None, **kwargs) -> Union[str, Generator]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        if stream:
            payload["stream"] = True

        try:
            res = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=kwargs.get("timeout", API_TIMEOUT),
                stream=stream,
            )
        except requests.exceptions.Timeout as exc:
            logger.error(f"[GroqProvider] Request timed out: {exc}")
            raise RuntimeError("The request timed out. Please try again.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error(f"[GroqProvider] Connection error: {exc}")
            raise RuntimeError("Could not connect to the AI service. Check your internet connection.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"[GroqProvider] Network error: {exc}")
            raise RuntimeError(f"Network error while contacting the AI service: {exc}") from exc

        if not res.ok:
            logger.error(f"[GroqProvider] HTTP Error {res.status_code}: {res.text[:200]}")
            raise RuntimeError(_friendly_http_error(res.status_code))

        if stream:
            def _stream_gen():
                try:
                    for line in res.iter_lines():
                        if line:
                            decoded = line.decode("utf-8").strip()
                            if decoded.startswith("data: "):
                                data_str = decoded[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except Exception as e:
                                    logger.warning(f"[GroqProvider] Chunk parse error: {e}")
                                    continue
                except Exception as exc:
                    logger.error(f"[GroqProvider] Streaming error: {exc}")
                    raise RuntimeError(f"Streaming error: {exc}") from exc
            return _stream_gen()
        else:
            try:
                data = res.json()
                choices = data.get("choices") or []
                if not choices:
                    raise ValueError("missing choices")

                reply = choices[0].get("message", {}).get("content")
                if not reply or not str(reply).strip():
                    raise ValueError("empty reply")
                return reply
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                logger.error(f"[GroqProvider] Response parsing error: {exc}")
                raise RuntimeError("I received an invalid response from the AI service. Please try again.") from exc


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        super().__init__(api_key=api_key or GEMINI_API_KEY, model=model or GEMINI_MODEL)
        self._client_configured = False

    def _ensure_configured(self):
        if not self._client_configured:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client_configured = True
            except ImportError as exc:
                logger.error("google-generativeai SDK not installed.")
                raise RuntimeError("google-generativeai SDK is not installed. Please run 'pip install google-generativeai'.") from exc

    def generate(self, messages: List[Dict[str, Any]], stream: bool = False, images: Optional[List[Any]] = None, **kwargs) -> Union[str, Generator]:
        self._ensure_configured()
        import google.generativeai as genai
        
        system_instruction = None
        history = []
        last_user_message = ""
        
        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = (system_instruction + "\n\n" + content).strip() if system_instruction else content
            elif idx == len(messages) - 1 and role == "user":
                last_user_message = content
            else:
                gemini_role = "model" if role in ("assistant", "model") else "user"
                history.append({"role": gemini_role, "parts": [content]})
                
        try:
            model_kwargs = {"model_name": self.model}
            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction
                
            model_obj = genai.GenerativeModel(**model_kwargs)
            
            contents = []
            for h in history:
                contents.append(h)
            
            current_parts = [last_user_message]
            if images:
                current_parts.extend(images)
            contents.append({"role": "user", "parts": current_parts})
            
            generation_config = genai.types.GenerationConfig(
                temperature=kwargs.get("temperature", 0.2),
            )
            
            if stream:
                response = model_obj.generate_content(contents, generation_config=generation_config, stream=True)
                def _stream_gen():
                    try:
                        for chunk in response:
                            if chunk.text:
                                yield chunk.text
                    except Exception as exc:
                        logger.error(f"[GeminiProvider] Stream error: {exc}")
                        raise RuntimeError(f"Gemini streaming error: {exc}") from exc
                return _stream_gen()
            else:
                response = model_obj.generate_content(contents, generation_config=generation_config, stream=False)
                if not response.text:
                    raise ValueError("Empty reply from Gemini.")
                return response.text
        except Exception as exc:
            logger.error(f"[GeminiProvider] API failure: {exc}")
            raise RuntimeError(f"Gemini service error: {exc}") from exc


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        super().__init__(api_key=api_key or OPENROUTER_API_KEY, model=model or OPENROUTER_MODEL)

    def generate(self, messages: List[Dict[str, Any]], stream: bool = False, images: Optional[List[Any]] = None, **kwargs) -> Union[str, Generator]:
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if images and msg is messages[-1] and role == "user":
                content_list = [{"type": "text", "text": content}]
                for img in images:
                    if isinstance(img, str):
                        content_list.append({"type": "image_url", "image_url": {"url": img}})
                formatted_messages.append({"role": role, "content": content_list})
            else:
                formatted_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        if stream:
            payload["stream"] = True

        try:
            res = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/enamulzishan/SARA",
                    "X-Title": "SARA AI Assistant",
                },
                json=payload,
                timeout=kwargs.get("timeout", API_TIMEOUT),
                stream=stream,
            )
        except requests.exceptions.Timeout as exc:
            logger.error(f"[OpenRouterProvider] Request timed out: {exc}")
            raise RuntimeError("The request timed out. Please try again.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error(f"[OpenRouterProvider] Connection error: {exc}")
            raise RuntimeError("Could not connect to OpenRouter service. Check your internet connection.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"[OpenRouterProvider] Network error: {exc}")
            raise RuntimeError(f"Network error while contacting OpenRouter: {exc}") from exc

        if not res.ok:
            logger.error(f"[OpenRouterProvider] HTTP Error {res.status_code}: {res.text[:200]}")
            raise RuntimeError(_friendly_http_error(res.status_code))

        if stream:
            def _stream_gen():
                try:
                    for line in res.iter_lines():
                        if line:
                            decoded = line.decode("utf-8").strip()
                            if decoded.startswith("data: "):
                                data_str = decoded[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except Exception as e:
                                    logger.warning(f"[OpenRouterProvider] Chunk parse error: {e}")
                                    continue
                except Exception as exc:
                    logger.error(f"[OpenRouterProvider] Streaming error: {exc}")
                    raise RuntimeError(f"Streaming error: {exc}") from exc
            return _stream_gen()
        else:
            try:
                data = res.json()
                choices = data.get("choices") or []
                if not choices:
                    raise ValueError("missing choices")

                reply = choices[0].get("message", {}).get("content")
                if not reply or not str(reply).strip():
                    raise ValueError("empty reply")
                return reply
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                logger.error(f"[OpenRouterProvider] Response parsing error: {exc}")
                raise RuntimeError("I received an invalid response from OpenRouter. Please try again.") from exc


def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    provider_name = (name or LLM_PROVIDER).strip().lower()
    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "openrouter":
        return OpenRouterProvider()
    else:
        logger.warning(f"Unknown LLM provider '{provider_name}', defaulting to Groq.")
        return GroqProvider()


def generate_with_fallback(messages: List[Dict[str, Any]], stream: bool = False, images: Optional[List[Any]] = None, **kwargs) -> Union[str, Generator]:
    """
    Generate completion using the primary provider, falling back to other configured
    providers if the primary provider hits a rate limit or encounters an error.
    """
    all_provider_names = ["groq", "gemini", "openrouter"]
    primary_name = LLM_PROVIDER.strip().lower()
    if primary_name not in all_provider_names:
        primary_name = "groq"
        
    provider_order = [primary_name] + [p for p in all_provider_names if p != primary_name]
    
    last_exc = None
    for p_name in provider_order:
        provider = get_llm_provider(p_name)
        if not provider.api_key:
            logger.info(f"[Fallback] Skipping provider '{p_name}' because API key is not configured.")
            continue
            
        try:
            logger.info(f"[Fallback] Attempting generation with provider '{p_name}'...")
            return provider.generate(messages, stream=stream, images=images, **kwargs)
        except Exception as exc:
            logger.warning(f"[Fallback] Provider '{p_name}' failed: {exc}. Trying next configured provider...")
            last_exc = exc
            
    if last_exc:
        raise last_exc
    raise RuntimeError("No configured LLM providers with valid API keys were able to generate a response.")


def _rollback_last_user_message():
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
    
    messages = [{"role": "system", "content": system_content}, {"role": "user", "content": message}]

    try:
        reply = generate_with_fallback(messages, stream=False, temperature=0.2)
    except Exception as exc:
        _rollback_last_user_message()
        logger.error(f"[ask_ai] Provider generation error: {exc}")
        return str(exc)

    memory.save_message("assistant", reply)
    memory.extract_and_save_facts(message, reply)
    return reply
