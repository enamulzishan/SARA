import pytest
from unittest.mock import patch, MagicMock

from ai.brain import (
    LLMProvider,
    GroqProvider,
    GeminiProvider,
    OpenRouterProvider,
    get_llm_provider,
    generate_with_fallback,
)


def test_get_llm_provider_factory():
    assert isinstance(get_llm_provider("groq"), GroqProvider)
    assert isinstance(get_llm_provider("gemini"), GeminiProvider)
    assert isinstance(get_llm_provider("openrouter"), OpenRouterProvider)
    # Default fallback for unknown provider
    assert isinstance(get_llm_provider("unknown_provider"), GroqProvider)


@patch("ai.brain.requests.post")
def test_groq_provider(mock_post):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Hello from Groq!"
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="test_groq_key", model="llama-3.3-70b-versatile")
    messages = [{"role": "user", "content": "Hi"}]
    reply = provider.generate(messages, stream=False)

    assert reply == "Hello from Groq!"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test_groq_key"
    assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"
    assert kwargs["json"]["messages"] == messages


@patch("ai.brain.GeminiProvider._ensure_configured")
@patch("google.generativeai.GenerativeModel")
def test_gemini_provider(mock_model_cls, mock_ensure_config):
    mock_model_obj = MagicMock()
    mock_model_obj.generate_content.return_value.text = "Hello from Gemini!"
    mock_model_cls.return_value = mock_model_obj

    provider = GeminiProvider(api_key="test_gemini_key", model="gemini-2.5-flash")
    messages = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "What is in this image?"}
    ]
    images = ["mock_image_bytes"]
    reply = provider.generate(messages, stream=False, images=images)

    assert reply == "Hello from Gemini!"
    mock_ensure_config.assert_called_once()
    mock_model_cls.assert_called_once_with(
        model_name="gemini-2.5-flash",
        system_instruction="Be helpful."
    )
    # Check that image was added to parts
    call_args = mock_model_obj.generate_content.call_args
    contents = call_args[0][0]
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert "mock_image_bytes" in contents[0]["parts"]


@patch("ai.brain.requests.post")
def test_openrouter_provider(mock_post):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Hello from OpenRouter!"
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    provider = OpenRouterProvider(api_key="test_or_key", model="openrouter/auto")
    messages = [{"role": "user", "content": "Describe this"}]
    images = ["https://example.com/test.png"]
    reply = provider.generate(messages, stream=False, images=images)

    assert reply == "Hello from OpenRouter!"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test_or_key"
    assert kwargs["headers"]["HTTP-Referer"] == "https://github.com/enamulzishan/SARA"
    assert kwargs["json"]["model"] == "openrouter/auto"
    # Check vision message formatting
    formatted_msgs = kwargs["json"]["messages"]
    assert len(formatted_msgs) == 1
    assert isinstance(formatted_msgs[0]["content"], list)
    assert formatted_msgs[0]["content"][0] == {"type": "text", "text": "Describe this"}
    assert formatted_msgs[0]["content"][1] == {"type": "image_url", "image_url": {"url": "https://example.com/test.png"}}


@patch("ai.brain.get_llm_provider")
@patch("ai.brain.LLM_PROVIDER", "groq")
def test_fallback_chain(mock_get_provider):
    mock_groq = MagicMock()
    mock_groq.api_key = "valid_groq_key"
    mock_groq.generate.side_effect = RuntimeError("Groq rate limit 429")

    mock_gemini = MagicMock()
    mock_gemini.api_key = "valid_gemini_key"
    mock_gemini.generate.return_value = "Recovered via Gemini!"

    def side_effect(name=None):
        if name == "groq":
            return mock_groq
        elif name == "gemini":
            return mock_gemini
        return MagicMock()

    mock_get_provider.side_effect = side_effect

    messages = [{"role": "user", "content": "Hello"}]
    reply = generate_with_fallback(messages, stream=False)

    assert reply == "Recovered via Gemini!"
    mock_groq.generate.assert_called_once_with(messages, stream=False, images=None)
    mock_gemini.generate.assert_called_once_with(messages, stream=False, images=None)


def test_check_provider_diagnostics():
    from check_api_keys import check_provider
    
    # 1. Test missing key
    res_missing = check_provider("Groq", GroqProvider, "", "test_model")
    assert res_missing["status"] == "Not configured"
    assert res_missing["icon"] == "⚠️"
    
    # 2. Test successful generation
    mock_provider_cls = MagicMock()
    mock_inst = mock_provider_cls.return_value
    mock_inst.generate.return_value = "Hello"
    res_ok = check_provider("TestOK", mock_provider_cls, "valid_key", "test_model")
    assert res_ok["status"] == "OK"
    assert res_ok["success"] is True
    assert "responded in" in res_ok["detail"]
    
    # 3. Test 401 error categorization
    mock_inst.generate.side_effect = RuntimeError("401 Unauthorized")
    res_401 = check_provider("TestAuth", mock_provider_cls, "bad_key", "test_model")
    assert res_401["status"] == "FAILED"
    assert "401/403" in res_401["detail"]
    
    # 4. Test rate limit 429 error categorization
    mock_inst.generate.side_effect = RuntimeError("429 Too Many Requests")
    res_429 = check_provider("TestRate", mock_provider_cls, "valid_key", "test_model")
    assert res_429["status"] == "FAILED"
    assert "429 Rate limit hit" in res_429["detail"]


@patch("check_api_keys.requests.get")
def test_check_serpapi_diagnostics(mock_get):
    from check_api_keys import check_serpapi
    
    # 1. Test missing key
    res_missing = check_serpapi("")
    assert res_missing["status"] == "Not configured"
    assert res_missing["icon"] == "⚠️"
    
    # 2. Test OK response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"organic_results": []}
    mock_get.return_value = mock_response
    
    res_ok = check_serpapi("valid_serp_key")
    assert res_ok["status"] == "OK"
    assert res_ok["success"] is True
    assert "responded in" in res_ok["detail"]
    
    # 3. Test 401 Unauthorized
    mock_response.status_code = 401
    res_401 = check_serpapi("bad_serp_key")
    assert res_401["status"] == "FAILED"
    assert "401 Unauthorized" in res_401["detail"]
    
    # 4. Test 429 Rate limit
    mock_response.status_code = 429
    res_429 = check_serpapi("rate_limited_key")
    assert res_429["status"] == "FAILED"
    assert "429 Rate limit exceeded" in res_429["detail"]
