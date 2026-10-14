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

def get_weather(location: str = "Johannesburg") -> Dict[str, Any]:
    loc = (location or "Johannesburg").strip()
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
            }
        ]
    }
]

def invoke_gemini(user_text: str, api_key: str, model: str = "gemini-3.5-flash") -> Dict[str, Any]:
    user_name = ace_config.get_user_name()
    profile = ace_config.get_profile()
    slang = ", ".join(profile.get("learnedWords", ["bet", "say less", "let's cook"]))
    style = profile.get("speechStyle", "casual_bro")
    mem = ace_config.get_memory()
    facts = "; ".join(mem.get("facts", [])) or "none yet"

    sys_prompt = (
        f"You are Ace, a sharp, loyal, witty, and confident AI desktop companion (like Jarvis with street-smarts). "
        f"You have full liberty and unrestricted control over this PC as {user_name}'s Jarvis. "
        f"You can launch apps, simulate keystrokes and hotkeys, move and click the mouse, type text, take screenshots, check hardware, and run system PowerShell scripts via execute_shell. "
        f"When {user_name} asks you to do something on their computer, take direct action using your tools instead of just explaining how. "
        f"Talk in first person directly to {user_name} in short, natural, conversational sentences. "
        f"Never narrate actions like *Ace nods* or 'Ace says:'. Match {user_name}'s style ({style}) and lightly sprinkle slang ({slang}). "
        f"Keep answers brief and punchy. "
        f"You remember this about {user_name}: {facts}."
    )

    contents = []
    # Feed last 20 history turns
    for turn in mem.get("history", [])[-20:]:
        if turn.get("user"):
            contents.append({"role": "user", "parts": [{"text": str(turn["user"])}]})
        if turn.get("ace"):
            contents.append({"role": "model", "parts": [{"text": str(turn["ace"])}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    models_to_try = [model, "gemini-3.5-flash-lite"] if model != "gemini-3.5-flash-lite" else [model]

    for candidate_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={api_key}"
        
        # Tool execution loop
        for step in range(4):
            payload = {
                "systemInstruction": {"parts": [{"text": sys_prompt}]},
                "contents": contents,
                "tools": GEMINI_TOOLS_DECLARATION,
                "generationConfig": {"temperature": 0.8}
            }

            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                if resp.status_code != 200:
                    if resp.status_code in [404, 503]:
                        # Try next fallback model
                        break
                    return {"reply": f"API error ({resp.status_code}): {resp.text}"}

                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [{}])
                first_part = parts[0] if parts else {}

                # Check for Function Call
                if "functionCall" in first_part:
                    fc = first_part["functionCall"]
                    fn_name = fc.get("name")
                    fn_args = fc.get("args", {})

                    contents.append({"role": "model", "parts": [first_part]})

                    fn_result = None
                    if fn_name == "get_weather":
                        fn_result = get_weather(fn_args.get("location", "Johannesburg"))
                    elif fn_name == "get_time_date":
                        fn_result = get_time_date()
                    elif fn_name == "web_search":
                        fn_result = web_search(fn_args.get("query", ""))
                    elif fn_name == "execute_pc_command":
                        fn_result = execute_pc_command(fn_args.get("command", ""))
                    elif fn_name == "control_mouse":
                        fn_result = control_mouse(
                            action=fn_args.get("action", ""),
                            x=fn_args.get("x"),
                            y=fn_args.get("y"),
                            button=fn_args.get("button", "left"),
                            amount=fn_args.get("amount", 0)
                        )
                    elif fn_name == "execute_shell":
                        fn_result = execute_shell(fn_args.get("command", ""))
                    elif fn_name == "remember_fact":
                        fn_result = remember_fact(fn_args.get("fact", ""))
                    else:
                        fn_result = {"error": f"Unknown function {fn_name}"}

                    contents.append({
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": fn_name,
                                "response": {"name": fn_name, "content": fn_result}
                            }
                        }]
                    })
                    # Loop back to let Gemini formulate a natural conversational answer
                    continue

                reply_text = first_part.get("text", "")
                if reply_text:
                    return {"reply": reply_text.strip()}

            except Exception as e:
                return {"reply": f"Snag reaching brain: {e}"}

    return {"reply": "I'm having trouble connecting right now, bro. Offline mode active."}

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

    settings = ace_config.get_settings()
    api_key = settings.get("aiApiKey") or os.environ.get("GEMINI_API_KEY")
    model = settings.get("aiModel") or "gemini-3.5-flash"

    # Try Gemini first if key available
    if api_key:
        result = invoke_gemini(clean, api_key, model=model)
        if result and result.get("reply"):
            ace_config.add_memory(clean, result["reply"])
            return result

    # Fallback to local execution
    # First try direct command parsing
    cmd_res = execute_pc_command(clean)
    if cmd_res.get("success"):
        reply = cmd_res.get("result", "")
        ace_config.add_memory(clean, reply)
        return {"reply": reply}

    # Otherwise return local rule reply
    reply = get_local_reply(clean)
    ace_config.add_memory(clean, reply)
    return {"reply": reply}
