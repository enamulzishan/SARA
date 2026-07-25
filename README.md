# SARA - Personal AI Assistant

SARA is a futuristic, highly capable personal AI assistant. Powered by a flexible **Multi-LLM Architecture** supporting **Groq**, **Google Gemini**, and **OpenRouter**, SARA features a modern web-based desktop interface, persistent SQLite memory, speech recognition, text-to-speech, live internet access via SerpAPI, and a built-in diagnostics suite.

---

## 🌟 Key Features

- **Multi-LLM Support:** Easily switch between providers via a clean abstraction layer (`LLMProvider`). Supports permanent free-tier models including Groq (Llama 3.3 70B), Google Gemini (2.5 Flash), and OpenRouter (auto-routing 30+ free models). Includes automatic fallback chaining if a provider fails or hits rate limits.
- **Built-in Diagnostics & Testing:** Features a standalone script (`check_api_keys.py`) and an integrated UI **Settings & Diagnostics** panel to test and verify all configured API keys (Groq, Gemini, OpenRouter, and SerpAPI) with real-time pass/fail status and latency reporting.
- **Modern Desktop UI:** Built using HTML/CSS/JS and packaged via `pywebview` for a seamless, native-feeling desktop experience with light/dark themes.
- **Persistent Memory & Context:**
  - **Conversations:** Remembers your current session context.
  - **Learned Facts:** Automatically extracts and remembers long-term facts about you (e.g., your name, preferences) across all sessions using an intelligent background extraction module.
  - **Memory Consent:** Privacy-first design with a non-blocking toast UI asking for your permission before saving any personal facts.
- **Real-time Web Search:** Automatically detects time-sensitive or factual queries and queries Google via SerpAPI to ensure SARA's answers are up-to-date and accurate.
- **Voice Capabilities:** 
  - **STT (Speech-to-Text):** Click the mic button to talk to SARA natively.
  - **TTS (Text-to-Speech):** SARA speaks her responses back to you. Click the mic while she's speaking to instantly interrupt her and start a new prompt.
- **Conversation Management:** Features a dedicated "History" tab to review past chats, a "Memory" tab to view/delete learned facts, and a "New Chat" button to seamlessly wipe context and start fresh.

---

## 🛠️ Tech Stack & Architecture

- **Backend Logic:** Python 3.12
- **Frontend UI:** Vanilla HTML, CSS, JavaScript 
- **Desktop Windowing:** `pywebview`
- **Database:** SQLite (`memory.db`)
- **LLM Engine:** Multi-LLM (`GroqProvider`, `GeminiProvider`, `OpenRouterProvider`) via `get_llm_provider`
- **Web Search:** SerpAPI
- **Speech Engines:** `SpeechRecognition` (STT), `pyttsx3` (TTS)

### Project Structure
- `main.py` - The main entry point that initializes the desktop window and exposes the JS bridge API.
- `ui/` - Contains the frontend (`index.html`, `app.js`, `style.css`).
- `assistant.py` - Core logic orchestrator bridging frontend actions to backend modules.
- `ai/brain.py` - Handles all LLM provider abstractions (`LLMProvider`, `GroqProvider`, `GeminiProvider`, `OpenRouterProvider`), SerpAPI search injection, fallback chaining, and message generation.
- `memory.py` - Handles SQLite connections, session generation, and background fact extraction.
- `speech/` - Contains STT and TTS modules.
- `data/` - Holds the local `memory.db` file (ignored by git).
- `settings.json` - Holds user preferences like theme, TTS muting, memory consent, and active LLM provider.
- `check_api_keys.py` - Standalone diagnostic script and runtime helper to verify provider API key validity and network latency.
- `test_providers.py` - Pytest unit tests verifying provider implementations and diagnostics with mocked API calls.

---

## 🚀 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/enamulzishan/SARA.git
   cd SARA
   ```

2. **Set up your environment:**
   Ensure you have Python 3.12 installed. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure you install `pywebview`, `google-generativeai`, `requests`, `pytest`, `SpeechRecognition`, `pyttsx3`, etc.)*

4. **Configure API Keys:**
   Copy `.env.example` to `.env` and configure your desired LLM provider and API keys:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=your_groq_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   SERPAPI_API_KEY=your_serpapi_key_here
   ```

5. **Run SARA:**
   ```bash
   python main.py
   ```

---

## 💡 Usage

- **Text Chat:** Simply type in the input bar at the bottom.
- **Voice Chat:** Click the microphone icon. SARA will listen to your voice. Click it again while she's talking to interrupt.
- **New Session:** Click the "New Chat" button in the sidebar to start a clean context window without restarting the app.
- **Themes & Sound:** Use the ☀️/🌙 icon in the sidebar to toggle dark mode, and the 🔊 icon in the top right to mute SARA's voice.
