import os
import sqlite3
import json
import uuid
import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "memory.db")

# Store session_id in memory per the user's instructions
CURRENT_SESSION_ID = str(uuid.uuid4())

def _get_connection():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Initialize database schema
_init_db()

def start_new_session():
    """Generates a new session ID for subsequent messages."""
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = str(uuid.uuid4())
    return CURRENT_SESSION_ID

def save_message(role, message):
    """Save a user or assistant message to the current session."""
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
            (CURRENT_SESSION_ID, role, message)
        )
        conn.commit()
    finally:
        conn.close()

def get_recent_history(limit=20):
    """Fetch recent messages from the *current* session only."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT role, message FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (CURRENT_SESSION_ID, limit)
        )
        rows = cursor.fetchall()
        # Reverse because we queried DESC to get the latest, but we need chronological order for the API
        return [{"role": row["role"], "content": row["message"]} for row in reversed(rows)]
    finally:
        conn.close()

def get_all_history_grouped():
    """Fetch all history ordered by timestamp DESC, grouped by session_id."""
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT session_id, role, message, timestamp FROM conversations ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        # Group by session_id but maintain overall descending order of sessions based on their latest message
        sessions_dict = {}
        session_order = []
        for row in rows:
            sid = row["session_id"]
            if sid not in sessions_dict:
                sessions_dict[sid] = {"session_id": sid, "latest_timestamp": row["timestamp"], "messages": []}
                session_order.append(sid)
            
            # Since we ordered DESC, appending here results in newest message first for each session
            sessions_dict[sid]["messages"].append({
                "role": row["role"],
                "content": row["message"],
                "timestamp": row["timestamp"]
            })
            
        return [sessions_dict[sid] for sid in session_order]
    finally:
        conn.close()

def get_all_facts():
    """Fetch all stored facts as a dict."""
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT key, value FROM facts")
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()

def forget_fact(key):
    """Delete a specific fact by key."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM facts WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()

def clear_history():
    """Wipe all conversation history entirely (destructive action)."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM conversations")
        conn.commit()
    finally:
        conn.close()
        
    # Also start a new session ID
    start_new_session()

def _upsert_fact(key, value):
    """Upsert a fact. SQLite doesn't have UPSERT before 3.24, so use REPLACE INTO."""
    conn = _get_connection()
    try:
        conn.execute(
            "REPLACE INTO facts (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        conn.commit()
    finally:
        conn.close()

def get_memory_enabled():
    import os, json
    settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f).get("memory_enabled", None)
        except Exception:
            pass
    return None

def extract_and_save_facts(user_message, llm_response):
    """
    Call the Groq API in the background to extract any personal facts
    from the exchange and conditionally upsert them into the database based on consent.
    """
    import threading
    import requests
    
    # We delay import config to avoid circular imports if any, but it's safe to import inside the worker
    def _worker():
        from ai.brain import API_URL
        from config import API_KEY, MODEL
        
        if not API_KEY:
            return
            
        system_prompt = (
            "You are a helpful data extraction module. Your job is to extract any durable personal facts "
            "about the user from their recent message. Return the facts ONLY as a valid JSON object of key-value pairs "
            "(e.g., {\"name\": \"John\", \"favorite_color\": \"blue\"}). "
            "If there are no personal facts to extract, return an empty JSON object: {}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        try:
            res = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if res.ok:
                data = res.json()
                reply = data["choices"][0]["message"]["content"]
                
                facts = json.loads(reply)
                if not facts:
                    return
                
                memory_enabled = get_memory_enabled()
                
                if memory_enabled is False:
                    return
                    
                if memory_enabled is True:
                    for k, v in facts.items():
                        _upsert_fact(k, str(v))
                    return
                    
                # If unset, prompt via UI
                import webview
                if webview.windows:
                    import base64
                    b64_facts = base64.b64encode(json.dumps(facts).encode('utf-8')).decode('utf-8')
                    webview.windows[0].evaluate_js(f"if (window.showMemoryConsentToast) window.showMemoryConsentToast('{b64_facts}')")
                
        except Exception as e:
            print(f"[FactExtraction] error: {e}")
            
    # Spawn and start daemon thread
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
