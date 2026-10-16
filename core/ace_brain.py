"""
Ace Brain Module - LLM Reasoning & Function Calling (Gemini 3.5 Flash)
Includes tools: Weather, Time/Date, Web Search, PC Commands, Memory.
"""
import os
import re
import json
import random
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests

from . import ace_config
from . import ace_actions

OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
}

# --- Tools Implementation ---

def get_weather(location: str = "Maputo") -> Dict[str, Any]:
    loc = (location or "").strip()
    if loc.lower() in ("", "current location", "current", "here", "local", "my location", "auto"):
        loc = ace_config.get_setting("defaultCity") or "Maputo"
    try:
        geo_resp = requests.get(
            OPEN_METEO_GEO_URL,
            params={"name": loc, "count": 1},
            timeout=8
        )
        geo_data = geo_resp.json()
        if not geo_data.get("results"):
            return {"error": f"Couldn't find location '{loc}'"}

        res = geo_data["results"][0]
        lat, lon = res["latitude"], res["longitude"]
        resolved_name = f"{res.get('name')}, {res.get('country')}"

        w_resp = requests.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto"
            },
            timeout=8
        )
        w_data = w_resp.json()
        curr = w_data.get("current", {})
        daily = w_data.get("daily", {})
        code = curr.get("weather_code", 0)

        return {
            "location": resolved_name,
            "condition": WEATHER_CODES.get(code, "Clear"),
            "temperature_c": curr.get("temperature_2m"),
            "feels_like_c": curr.get("apparent_temperature"),
            "humidity": curr.get("relative_humidity_2m"),
            "wind_speed_kmh": curr.get("wind_speed_10m"),
            "today_high_c": daily.get("temperature_2m_max", [None])[0],
            "today_low_c": daily.get("temperature_2m_min", [None])[0],
            "rain_chance_pct": daily.get("precipitation_probability_max", [None])[0]
        }
    except Exception as e:
        return {"error": f"Weather lookup failed: {e}"}

def get_time_date() -> Dict[str, str]:
    now = datetime.now()
    return {
        "time": now.strftime("%I:%M %p").lstrip("0"),
        "date": now.strftime("%A, %B %d, %Y"),
        "timestamp": now.isoformat()
    }

def web_search(query: str) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"error": "Empty search query"}
    try:
        # Use DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        resp = requests.get(
            url,
            params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8
        )
        data = resp.json()
        abstract = data.get("AbstractText")
        answer = data.get("Answer")
        related = [t.get("Text") for t in data.get("RelatedTopics", []) if isinstance(t, dict) and t.get("Text")]

        summary = answer or abstract
        if not summary and related:
            summary = "; ".join(related[:3])

        if summary:
            return {"query": q, "result": summary}

        # Fallback to direct web lookup
        return {"query": q, "result": f"Searched web for '{q}'. No direct instant snippet found."}
    except Exception as e:
        return {"error": f"Search failed: {e}"}

def execute_pc_command(command: str) -> Dict[str, Any]:
    cmd = (command or "").strip()
    c_lower = cmd.lower()

    if c_lower.startswith("open "):
        target = cmd[5:].strip()
        rep = ace_actions.open_target(target)
        return {"success": True, "result": rep}

    if c_lower.startswith("type "):
        text = cmd[5:]
        ace_actions.type_text(text)
        return {"success": True, "result": f"Typed '{text}'"}

    if c_lower == "screenshot":
        path = ace_actions.take_screenshot()
        return {"success": True, "result": f"Screenshot saved to {path}"}

    if c_lower.startswith("volume "):
        action = c_lower[7:].strip()
        rep = ace_actions.set_volume(action)
        return {"success": True, "result": rep}

    if c_lower.startswith("press "):
        combo = c_lower[6:].strip()
        ace_actions.send_key_combo(combo)
        return {"success": True, "result": f"Pressed {combo}"}

    if c_lower == "status":
        metrics = ace_actions.get_pc_metrics()
        return {"success": True, "result": f"RAM: {metrics.get('ram_percent')}% used ({metrics.get('ram_used_gb')}/{metrics.get('ram_total_gb')} GB), CPU: {metrics.get('cpu')}%"}

    return {"success": False, "result": f"Unknown command: '{command}'"}

def remember_fact(fact: str) -> Dict[str, Any]:
    ace_config.add_fact(fact)
    return {"success": True, "message": f"Saved '{fact}' to memory."}

def control_mouse(action: str, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", amount: int = 0) -> Dict[str, Any]:
    act = (action or "").lower()
    if act == "move" and x is not None and y is not None:
        return {"success": True, "result": ace_actions.move_mouse(x, y)}
    elif act == "click":
        return {"success": True, "result": ace_actions.click(x, y, button=button)}
    elif act == "double_click":
        return {"success": True, "result": ace_actions.double_click(x, y)}
    elif act == "right_click":
        return {"success": True, "result": ace_actions.right_click(x, y)}
    elif act == "drag" and x is not None and y is not None:
        return {"success": True, "result": ace_actions.drag_mouse(x, y)}
    elif act == "scroll":
        return {"success": True, "result": ace_actions.scroll(amount)}
    pos = ace_actions.get_mouse_position()
    return {"success": True, "cursor_position": pos}

def execute_shell(command: str) -> Dict[str, Any]:
    res = ace_actions.run_shell(command)
    return {"success": True, "output": res}

# --- Gemini API Caller ---

GEMINI_TOOLS_DECLARATION = [
    {
        "functionDeclarations": [
            {
                "name": "get_weather",
                "description": "Get current weather for a location.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "location": {"type": "STRING", "description": "City or location name"}
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_time_date",
                "description": "Get current local time and date.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "web_search",
                "description": "Search the web for up-to-date facts, information, and answers.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "execute_pc_command",
                "description": "Control the PC. Valid commands: open <app/site/folder>, type <text>, screenshot, volume up/down/mute, press <key_combo/hotkey>, status, lock",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "PC command to run"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "control_mouse",
                "description": "Directly control mouse pointer: move to coordinates, click, double_click, right_click, drag, or scroll.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "Action: 'move', 'click', 'double_click', 'right_click', 'drag', 'scroll'"},
                        "x": {"type": "INTEGER", "description": "X coordinate on screen"},
                        "y": {"type": "INTEGER", "description": "Y coordinate on screen"},
                        "button": {"type": "STRING", "description": "'left' or 'right'"},
                        "amount": {"type": "INTEGER", "description": "Scroll ticks (positive up, negative down)"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "execute_shell",
                "description": "Execute raw PowerShell or CMD system commands directly on Windows with full administrative capability. Create files, launch scripts, manage processes.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "PowerShell command string to execute"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "remember_fact",
                "description": "Save an important personal fact or preference about the user into long-term memory.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fact": {"type": "STRING", "description": "The fact to remember"}
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "write_document",
                "description": "Open Microsoft Word (or Notepad) and write a complete essay, speech, formal greeting, letter, report, or document directly into it. Generate the full, rich text yourself and pass it in 'content'.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Heading or title of the document/essay/speech"},
                        "content": {"type": "STRING", "description": "The full multi-paragraph text of the essay, speech, greeting, or document to write inside Word/Notepad"},
                        "app": {"type": "STRING", "description": "'word' (default) or 'notepad'"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "send_whatsapp_message",
                "description": "Open WhatsApp Desktop, search for a contact by name or phone number, type the message into their chat, and send it.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "contact": {"type": "STRING", "description": "Contact name (e.g. 'Mom', 'João') or phone number"},
                        "message": {"type": "STRING", "description": "The message text to send"},
                        "send": {"type": "BOOLEAN", "description": "True to press Enter and send immediately (default True), False to only type it in the box"}
                    },
                    "required": ["contact", "message"]
                }
            },
            {
                "name": "spotify_control",
                "description": "Search and play a song, artist, genre, or playlist inside Spotify, or pause/resume/skip tracks.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "'play', 'pause', 'next', or 'previous'"},
                        "query": {"type": "STRING", "description": "Song, artist, or genre to search and play in Spotify (leave empty for pause/next/previous)"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "type_in_app",
                "description": "Focus or launch any application window, optionally press a keyboard shortcut first (like 'ctrl+n' or 'ctrl+f'), and paste/type text directly inside that app.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "app_name": {"type": "STRING", "description": "Application name or window title to focus/open (e.g. 'word', 'notepad', 'chrome', 'whatsapp')"},
                        "text": {"type": "STRING", "description": "The text to paste/type into the application"},
                        "press_enter": {"type": "BOOLEAN", "description": "Whether to press Enter after typing (default False)"},
                        "shortcut_before": {"type": "STRING", "description": "Optional shortcut to trigger before typing, e.g. 'ctrl+n', 'ctrl+l', 'ctrl+f'"}
                    },
                    "required": ["app_name", "text"]
                }
            }
        ]
    }
]

FAST_MODEL = "gemini-3.5-flash-lite"
SMART_MODEL = "gemini-3.5-flash"
HISTORY_TURNS = 10
REQUEST_TIMEOUT = (5, 25)      # (connect, read) seconds per HTTP call
TOTAL_DEADLINE_SEC = 45        # hard cap for one ask, across retries/fallbacks

_ERROR_MARKERS = ("Snag reaching brain", "API error (", "trouble connecting", "Offline mode active", "Done, bro.")


def _is_error_reply(text: str) -> bool:
    return any(m in (text or "") for m in _ERROR_MARKERS)


def _summarize_tool_results(results: List[Dict[str, Any]]) -> str:
    """Fallback human-readable summary when a tool succeeded but the follow-up LLM call hit 503."""
    pieces = []
    for item in results:
        if not isinstance(item, dict):
            continue
        if "temperature_c" in item and "location" in item:
            pieces.append(
                f"It's {item.get('temperature_c')}°C ({item.get('condition', 'clear').lower()}) in {item.get('location')}, "
                f"feels like {item.get('feels_like_c')}°C, bro."
            )
        elif item.get("output"):
            out = re.sub(r"\s+", " ", str(item["output"])).strip()
            pieces.append(out[:240])
        elif item.get("result"):
            pieces.append(str(item["result"]))
        elif item.get("message"):
            pieces.append(str(item["message"]))
    return " ".join(pieces).strip() or "All done, bro."


def _thinking_config(model: str) -> Optional[Dict[str, Any]]:
    """Keep thinking low so replies come back fast (measured: flash 22s -> 11s, lite ~4s)."""
    if "lite" in model:
        return None  # lite default is already fast; thinkingBudget=0 is rejected
    return {"thinkingBudget": 0}


def _dispatch_tool(fn_name: str, fn_args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if fn_name == "get_weather":
            return get_weather(fn_args.get("location", "Maputo"))
        if fn_name == "get_time_date":
            return get_time_date()
        if fn_name == "web_search":
            return web_search(fn_args.get("query", ""))
        if fn_name == "execute_pc_command":
            return execute_pc_command(fn_args.get("command", ""))
        if fn_name == "control_mouse":
            return control_mouse(
                action=fn_args.get("action", ""),
                x=fn_args.get("x"),
                y=fn_args.get("y"),
                button=fn_args.get("button", "left"),
                amount=fn_args.get("amount", 0),
            )
        if fn_name == "execute_shell":
            return execute_shell(fn_args.get("command", ""))
        if fn_name == "remember_fact":
            return remember_fact(fn_args.get("fact", ""))
        if fn_name == "write_document":
            res = ace_actions.write_document(
                content=fn_args.get("content", ""),
                title=fn_args.get("title", ""),
                app=fn_args.get("app", "word"),
            )
            return {"success": True, "result": res}
        if fn_name == "send_whatsapp_message":
            res = ace_actions.send_whatsapp_message(
                contact=fn_args.get("contact", ""),
                message=fn_args.get("message", ""),
                send=bool(fn_args.get("send", True)),
            )
            return {"success": True, "result": res}
        if fn_name == "spotify_control":
            res = ace_actions.spotify_control(
                action=fn_args.get("action", "play"),
                query=fn_args.get("query", ""),
            )
            return {"success": True, "result": res}
        if fn_name == "type_in_app":
            res = ace_actions.type_in_app(
                app_name=fn_args.get("app_name", ""),
                text=fn_args.get("text", ""),
                press_enter=bool(fn_args.get("press_enter", False)),
                shortcut_before=fn_args.get("shortcut_before", ""),
            )
            return {"success": True, "result": res}
        return {"error": f"Unknown function {fn_name}"}
    except Exception as e:
        return {"error": f"{fn_name} failed: {e}"}


def invoke_gemini(user_text: str, api_key: str, model: str = FAST_MODEL) -> Dict[str, Any]:
    """Returns {"reply": str} on success, or {"error": str} if every model failed."""
    import time as _time

    user_name = ace_config.get_user_name()
    profile = ace_config.get_profile()
    slang = ", ".join(profile.get("learnedWords", ["bet", "say less", "let's cook"]))
    style = profile.get("speechStyle", "casual_bro")
    mem = ace_config.get_memory()
    facts = "; ".join(mem.get("facts", [])) or "none yet"

    sys_prompt = (
        f"You are Ace, a sharp, loyal, witty, and confident AI desktop companion (like Jarvis with street-smarts). "
        f"You have full liberty and unrestricted control over this PC and inside applications as {user_name}'s Jarvis. "
        f"When {user_name} asks to write an essay, speech, greeting, letter, or text in Word or Notepad, ALWAYS call write_document with the complete, well-written text in 'content'. "
        f"When {user_name} asks to text/message someone on WhatsApp, ALWAYS call send_whatsapp_message with the contact name/number and message. "
        f"When {user_name} asks to play or control music on Spotify, call spotify_control. "
        f"When {user_name} asks to type or interact inside any other app, use type_in_app or execute_shell. "
        f"Take direct action using your tools instead of explaining how. "
        f"Talk in first person directly to {user_name} in short, natural, conversational sentences. "
        f"Never narrate actions like *Ace nods* or 'Ace says:'. Match {user_name}'s style ({style}) and lightly sprinkle slang ({slang}). "
        f"Reply in the same language {user_name} uses (e.g. Portuguese if they speak Portuguese). "
        f"Keep your spoken reply brief and punchy (1-2 sentences) even when you write a long document via write_document. "
        f"Current local time: {datetime.now().strftime('%A %d %B %Y, %H:%M')}. "
        f"You remember this about {user_name}: {facts}."
    )

    base_contents = []
    # Feed recent history, skipping turns where Ace only returned an error
    for turn in mem.get("history", [])[-HISTORY_TURNS:]:
        if not turn.get("user") or not turn.get("ace") or _is_error_reply(turn["ace"]):
            continue
        base_contents.append({"role": "user", "parts": [{"text": str(turn["user"])}]})
        base_contents.append({"role": "model", "parts": [{"text": str(turn["ace"])}]})
    base_contents.append({"role": "user", "parts": [{"text": user_text}]})

    models_to_try = [model] + [m for m in (FAST_MODEL, SMART_MODEL) if m != model]
    deadline = _time.monotonic() + TOTAL_DEADLINE_SEC
    last_error = "unknown error"

    for candidate_model in models_to_try:
        if _time.monotonic() > deadline:
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent"
        contents = list(base_contents)  # fresh copy per model
        thinking = _thinking_config(candidate_model)
        tools_ran = False
        last_tool_results: List[Dict[str, Any]] = []
        retried_503 = False

        # Tool execution loop
        for step in range(5):
            if _time.monotonic() > deadline:
                last_error = "took too long"
                break
            gen_cfg: Dict[str, Any] = {"temperature": 0.8}
            if thinking:
                gen_cfg["thinkingConfig"] = thinking
            payload = {
                "systemInstruction": {"parts": [{"text": sys_prompt}]},
                "contents": contents,
                "tools": GEMINI_TOOLS_DECLARATION,
                "generationConfig": gen_cfg,
            }

            try:
                resp = requests.post(
                    url, json=payload,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.exceptions.RequestException as e:
                last_error = f"{candidate_model}: {type(e).__name__}"
                break  # timeout / network -> next model

            if resp.status_code != 200:
                body = resp.text[:300]
                last_error = f"{candidate_model}: HTTP {resp.status_code}"
                if resp.status_code == 400 and thinking and "hink" in body:
                    thinking = None  # model rejects this thinking config; retry without it
                    continue
                if resp.status_code in (429, 500, 502, 503, 504) and tools_ran and not retried_503:
                    retried_503 = True
                    _time.sleep(0.8)
                    continue
                if resp.status_code in (401, 403):
                    return {"error": "API key rejected (check aiApiKey in settings)."}
                break  # 404/429/5xx/other -> next model

            try:
                data = resp.json()
                candidate = (data.get("candidates") or [{}])[0]
                parts = (candidate.get("content") or {}).get("parts") or []
            except Exception as e:
                last_error = f"{candidate_model}: bad response ({e})"
                break

            calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if calls:
                # Echo the model turn back unchanged (keeps thoughtSignature for Gemini 3)
                contents.append({"role": "model", "parts": parts})
                responses = []
                for fc in calls:
                    fn_name = fc.get("name")
                    fn_result = _dispatch_tool(fn_name, fc.get("args") or {})
                    last_tool_results.append(fn_result)
                    responses.append({
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"name": fn_name, "content": fn_result},
                        }
                    })
                contents.append({"role": "user", "parts": responses})
                tools_ran = True
                continue  # let Gemini formulate a natural answer

            reply_text = " ".join(
                p["text"] for p in parts if p.get("text") and not p.get("thought")
            ).strip()
            if reply_text:
                return {"reply": reply_text}
            last_error = f"{candidate_model}: empty reply ({candidate.get('finishReason', '?')})"
            break

        if tools_ran:
            # Actions were already executed; summarize the tool results directly rather than re-running tools.
            return {"reply": _summarize_tool_results(last_tool_results)}

    return {"error": last_error}

# --- Offline Rule Matcher ---

def get_local_reply(user_text: str) -> str:
    n = ace_config.get_user_name()
    t = user_text.lower().strip()

    if re.search(r"who (made|created|built) you", t):
        return f"You did, {n}. Project Jarvis. I'm Ace, your guy in the corner."
    if re.search(r"who are you|what are you|your name", t):
        return "I'm Ace. Your friend, co-pilot, and desktop companion."
    if re.search(r"what can you do|help|commands", t):
        return "Talk to me like normal. Or tell me to open apps, search Google, type text, screenshot, or check the weather."
    if re.search(r"love you|you're (the best|awesome|cool)|good job|thank|thx|appreciate", t):
        return random.choice([f"Always, {n}.", "Real recognize real.", "Say less. I got you."])
    if re.search(r"good night|going to sleep|bye|see you|later", t):
        return random.choice([f"Later {n}. I'll be right here.", "Sleep well, bro."])
    if re.search(r"what time|the time", t):
        return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}, {n}."
    if re.search(r"what day|the date|today", t):
        return f"Today is {datetime.now().strftime('%A, %B %d')}."
    if re.search(r"^(yo|hey|hi|hello|sup|what's up|whats up|wassup|ayo)\b", t):
        return random.choice([f"Yo {n}! What's the move?", f"What's good {n}! I'm here.", "Ayy, talk to me."])

    return random.choice([
        f"I hear you, {n}. Tell me what to launch or search.",
        "Real. What's next on the PC?",
        "Say less. Want me to open that up?"
    ])

# --- Main Entry Point ---

def ask_ace(user_input: str) -> Dict[str, Any]:
    clean = re.sub(r"^(hey|yo|ok|okay)?\s*ace[,\s]+", "", user_input.strip(), flags=re.IGNORECASE).strip()
    if not clean:
        return {"reply": "Yo, I'm here. What's up?"}

    # Instant answers that don't need the cloud brain (zero latency)
    fast = _fast_local_reply(clean)
    if fast:
        ace_config.add_memory(clean, fast)
        return {"reply": fast}

    settings = ace_config.get_settings()
    api_key = settings.get("aiApiKey") or os.environ.get("GEMINI_API_KEY")
    model = settings.get("aiModel") or FAST_MODEL

    # Try Gemini first if key available
    api_error = None
    if api_key:
        result = invoke_gemini(clean, api_key, model=model)
        if result.get("reply"):
            ace_config.add_memory(clean, result["reply"])
            return result
        api_error = result.get("error")
        print(f"[AceBrain] Gemini failed: {api_error}")

    # Fallback to local execution
    # First try direct command parsing
    cmd_res = execute_pc_command(clean)
    if cmd_res.get("success"):
        reply = cmd_res.get("result", "")
        ace_config.add_memory(clean, reply)
        return {"reply": reply}

    if api_error:
        # Be honest instead of giving a random canned line; don't pollute memory.
        return {"reply": "My brain's connection is lagging right now, bro. Hit me again in a sec.",
                "error": api_error}

    # No API key: return local rule reply
    reply = get_local_reply(clean)
    ace_config.add_memory(clean, reply)
    return {"reply": reply}


_TIME_RE = re.compile(r"^(what('?s| is) the time|what time is it|time\??|que horas s[aã]o)\??$")
_DATE_RE = re.compile(r"^(what('?s| is) (the date|today('?s date)?)|what day is (it|today)|date\??)\??$")


def _fast_local_reply(text: str) -> Optional[str]:
    t = re.sub(r"[!.?]+$", "", text.lower().strip())
    n = ace_config.get_user_name()
    if _TIME_RE.match(t):
        return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}, {n}."
    if _DATE_RE.match(t):
        return f"Today is {datetime.now().strftime('%A, %B %d')}, {n}."
    # Simple single-step PC commands: "open <known app/url>", "volume up", "screenshot", "status"
    m = re.match(r"^open (?:the |my )?(.+?)(?: app| please)?$", t)
    if m:
        target = m.group(1).strip()
        known = target in getattr(ace_actions, "APP_ALIASES", {}) or re.search(r"\.\w{2,4}$|^https?://", target)
        if not known:
            return None  # let Gemini interpret it (typos, "open a song on spotify", ...)
    if m or re.match(r"^(volume (up|down|mute)|screenshot|status)$", t):
        res = execute_pc_command(t)
        if res.get("success"):
            return str(res.get("result", "Done."))
    return None

