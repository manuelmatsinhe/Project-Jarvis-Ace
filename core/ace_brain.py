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
    cmd = (command or "").strip().rstrip(".!?")
    c_lower = cmd.lower()

    # 1. Open / Launch / Start / Run
    open_m = re.match(
        r"^(?:can\s+you\s+|please\s+)?(?:open|launch|start|run|abre|abrir|iniciar)\s+(?:up\s+)?(.+)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if open_m:
        target = open_m.group(1).strip()
        # Check if it's "open new tab" / "open task view"
        if target.lower() in ("new tab", "a new tab"):
            return {"success": True, "result": ace_actions.window_control("new_tab")}
        rep = ace_actions.open_target(target)
        return {"success": True, "result": rep}

    # 2. Close / Quit / Kill / Exit app or window
    close_m = re.match(
        r"^(?:can\s+you\s+|please\s+)?(?:close|quit|kill|exit|stop|terminate|fechar|fecha)\s+(.+)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if close_m:
        target = close_m.group(1).strip()
        if target.lower() in ("tab", "current tab", "this tab"):
            return {"success": True, "result": ace_actions.window_control("close_tab")}
        rep = ace_actions.close_app(target)
        return {"success": True, "result": rep}

    # 3. Scan / Search PC / List installed apps or shortcuts
    scan_m = re.match(
        r"^(?:scan|scan\s+pc|search\s+pc|find\s+on\s+pc|list\s+installed\s+apps|list\s+shortcuts|show\s+my\s+shortcuts|what\s+apps\s+do\s+i\s+have)(?:\s+(?:for\s+)?(.+))?$",
        cmd,
        flags=re.IGNORECASE,
    )
    if scan_m:
        q = (scan_m.group(1) or "").strip()
        cat = "all"
        if "shortcut" in c_lower and not q:
            cat = "shortcuts"
        elif q.lower() in ("shortcuts", "shortcut", "atalhos", "apps", "programs", "desktop", "files", "folders"):
            cat = q.lower()
            q = ""
        return ace_actions.scan_pc(query=q, category=cat, launch_best=False)

    # 4. List open / running windows
    if c_lower in ("running apps", "open windows", "list open windows", "what is open", "what apps are open", "active windows"):
        return {"success": True, "result": ace_actions.list_running_apps()}

    # 5. Window & Tab controls
    if c_lower in ("show desktop", "minimize all", "hide all windows", "desktop view", "go to desktop"):
        return {"success": True, "result": ace_actions.window_control("show_desktop")}
    if c_lower in ("switch window", "next window", "alt tab", "switch app"):
        return {"success": True, "result": ace_actions.window_control("switch")}
    if c_lower in ("task view", "show all windows"):
        return {"success": True, "result": ace_actions.window_control("task_view")}
    if c_lower in ("snap left", "dock left", "move window left", "window left"):
        return {"success": True, "result": ace_actions.window_control("snap_left")}
    if c_lower in ("snap right", "dock right", "move window right", "window right"):
        return {"success": True, "result": ace_actions.window_control("snap_right")}
    if c_lower in ("new tab", "open new tab"):
        return {"success": True, "result": ace_actions.window_control("new_tab")}
    if c_lower in ("close tab", "close this tab", "close current tab"):
        return {"success": True, "result": ace_actions.window_control("close_tab")}
    if c_lower in ("reopen tab", "restore tab", "undo close tab"):
        return {"success": True, "result": ace_actions.window_control("reopen_tab")}
    if c_lower in ("next tab", "switch tab"):
        return {"success": True, "result": ace_actions.window_control("next_tab")}
    if c_lower in ("previous tab", "prev tab", "last tab"):
        return {"success": True, "result": ace_actions.window_control("prev_tab")}
    if c_lower in ("refresh", "reload", "reload page", "refresh page"):
        return {"success": True, "result": ace_actions.window_control("refresh")}
    if c_lower in ("fullscreen", "full screen", "toggle fullscreen"):
        return {"success": True, "result": ace_actions.window_control("fullscreen")}
    if c_lower in ("zoom in", "make bigger"):
        return {"success": True, "result": ace_actions.window_control("zoom_in")}
    if c_lower in ("zoom out", "make smaller"):
        return {"success": True, "result": ace_actions.window_control("zoom_out")}

    win_m = re.match(r"^(minimize|maximize|restore|focus|bring\s+to\s+front)(?:\s+(.+))?$", cmd, flags=re.IGNORECASE)
    if win_m:
        act = win_m.group(1).lower().replace("bring to front", "focus")
        tgt = (win_m.group(2) or "").strip()
        if tgt.lower() in ("window", "this", "this window", "current window", "active window"):
            tgt = ""
        return {"success": True, "result": ace_actions.window_control(act, tgt)}

    # 6. Media playback controls & YouTube/Spotify/Browser searches
    if c_lower in ("play", "pause", "resume", "play pause", "pause music", "resume music", "stop music"):
        return {"success": True, "result": ace_actions.media_control("play_pause")}
    if c_lower in ("next", "next track", "next song", "skip", "skip song", "skip track"):
        return {"success": True, "result": ace_actions.media_control("next")}
    if c_lower in ("previous", "previous track", "previous song", "prev song", "prev track", "back track"):
        return {"success": True, "result": ace_actions.media_control("previous")}

    yt_m = re.match(
        r"^(?:search|play|watch|find|look\s+up)\s+(.+?)\s+(?:on|in)\s+youtube$|^youtube\s+(?:search\s+)?(.+)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if yt_m:
        q = (yt_m.group(1) or yt_m.group(2) or "").strip()
        return {"success": True, "result": ace_actions.youtube_control("search", q)}

    sp_m = re.match(
        r"^(?:play|search|listen\s+to)\s+(.+?)\s+(?:on|in)\s+spotify$|^spotify\s+(?:play\s+)?(.+)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if sp_m:
        q = (sp_m.group(1) or sp_m.group(2) or "").strip()
        return {"success": True, "result": ace_actions.spotify_control("play", q)}

    search_on_m = re.match(
        r"^(?:search|look\s+up|find)(?:\s+for)?\s+(.+?)\s+(?:on|in)\s+(google|bing|duckduckgo|github|reddit|amazon|wikipedia)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if search_on_m:
        return {"success": True, "result": ace_actions.browser_search(search_on_m.group(1), search_on_m.group(2))}

    google_m = re.match(r"^(?:google|search\s+google\s+for|search\s+the\s+web\s+for)\s+(.+)$", cmd, flags=re.IGNORECASE)
    if google_m:
        return {"success": True, "result": ace_actions.browser_search(google_m.group(1), "google")}

    # In-App Awareness & Free Movement / Touch Controls
    if re.search(r"\b(?:what\s+app\s+am\s+i\s+in|where\s+am\s+i|what\s+window\s+is\s+this|current\s+app|active\s+app|what\s+is\s+open\s+now)\b", c_lower):
        return {"success": True, "result": ace_actions.describe_current_app()}

    click_m = re.match(
        r"^(?:can\s+you\s+|please\s+)?(?:click|touch|press|tap|hit|selecionar|clicar)\s+(?:on\s+|no\s+|na\s+)?(.+?)(?:\s+in\s+this\s+app|\s+please|\s+for\s+me)?$",
        cmd,
        flags=re.IGNORECASE,
    )
    if click_m and not any(k in c_lower for k in ("button", "key", "hotkey")):
        target_el = click_m.group(1).strip()
        if target_el.lower() not in ("volume", "brightness"):
            return {"success": True, "result": ace_actions.click_app_element(target_el)}

    in_app_search_m = re.match(
        r"^(?:search|find|look\s+up|pesquisar)\s+(?:for\s+)?(.+?)\s+(?:here|in\s+this\s+app|in\s+here)$",
        cmd,
        flags=re.IGNORECASE,
    )
    if in_app_search_m:
        return {"success": True, "result": ace_actions.in_app_search(in_app_search_m.group(1).strip())}

    scroll_m = re.match(
        r"^(?:can\s+you\s+|please\s+)?(?:scroll|descer|subir)(?:\s+(down|up|descer|subir))?(?:\s+(\d+))?$",
        c_lower,
    )
    if scroll_m or c_lower in ("scroll down", "scroll up", "scroll", "descer", "subir", "page down", "page up"):
        direction = "scroll_down"
        if "up" in c_lower or "subir" in c_lower:
            direction = "scroll_up"
        elif "page down" in c_lower:
            direction = "page_down"
        elif "page up" in c_lower:
            direction = "page_up"
        amount = int(scroll_m.group(2)) if (scroll_m and scroll_m.group(2)) else 1
        return {"success": True, "result": ace_actions.app_navigate(direction, amount=amount)}

    # 7. Volume & Brightness
    if c_lower in ("mute", "unmute", "toggle mute"):
        return {"success": True, "result": ace_actions.set_volume("mute")}
    vol_m = re.match(r"^(?:set\s+)?volume\s+(?:to\s+)?(.+)$|^(?:turn\s+)?(up|down)\s+(?:the\s+)?volume$", c_lower)
    if vol_m:
        act = (vol_m.group(1) or vol_m.group(2) or "").strip()
        return {"success": True, "result": ace_actions.set_volume(act)}

    bright_m = re.match(r"^(?:set\s+)?brightness\s+(?:to\s+)?(.+)$|^(?:turn\s+)?(up|down)\s+(?:the\s+)?brightness$", c_lower)
    if bright_m:
        act = (bright_m.group(1) or bright_m.group(2) or "").strip()
        return {"success": True, "result": ace_actions.set_brightness(act)}

    # 8. Type & Press Keys
    if c_lower.startswith("type "):
        text = cmd[5:]
        ace_actions.type_text(text)
        return {"success": True, "result": f"Typed '{text}'"}

    if c_lower.startswith("press "):
        combo = c_lower[6:].strip()
        ace_actions.send_key_combo(combo)
        return {"success": True, "result": f"Pressed {combo}"}

    # 9. Screenshot, Recycle Bin, Clipboard, Network, Power, Status
    if c_lower in ("screenshot", "take screenshot", "take a screenshot", "capture screen", "print screen"):
        path = ace_actions.take_screenshot()
        return {"success": True, "result": f"Screenshot saved to {path}"}

    if c_lower in ("empty recycle bin", "clear recycle bin", "clean recycle bin"):
        return {"success": True, "result": ace_actions.empty_recycle_bin()}

    if c_lower in ("clipboard", "read clipboard", "what is on my clipboard", "whats on my clipboard", "show clipboard"):
        return {"success": True, "result": ace_actions.get_clipboard()}

    if c_lower in ("ip", "ip address", "my ip", "what is my ip", "wifi", "network", "network info", "wifi name"):
        return {"success": True, "result": ace_actions.get_network_info()}

    if c_lower in ("lock", "lock pc", "lock screen", "lock computer", "lock workstation"):
        return {"success": True, "result": ace_actions.lock_workstation()}

    if c_lower in ("sleep", "put pc to sleep", "go to sleep", "hibernate"):
        return {"success": True, "result": ace_actions.system_power("sleep")}

    if c_lower in ("shutdown", "shut down", "shut down pc", "turn off pc", "power off"):
        return {"success": True, "result": ace_actions.system_power("shutdown")}

    if c_lower in ("restart pc", "reboot", "reboot pc"):
        return {"success": True, "result": ace_actions.system_power("restart")}

    if c_lower in ("cancel shutdown", "abort shutdown"):
        return {"success": True, "result": ace_actions.system_power("cancel_shutdown")}

    if c_lower in ("status", "system status", "pc status", "specs", "battery", "battery level", "cpu", "ram", "memory", "disk", "storage", "free space"):
        m = ace_actions.get_pc_metrics()
        bat_str = f", Battery: {m['battery']}% ({'charging' if m.get('charging') else 'on battery'})" if m.get("battery") is not None else ""
        disk_str = f", Disk C: {m.get('disk_free_gb')} GB free ({m.get('disk_percent')}% used)" if m.get("disk_total_gb") else ""
        return {
            "success": True,
            "result": f"CPU: {m.get('cpu')}% | RAM: {m.get('ram_percent')}% ({m.get('ram_used_gb')}/{m.get('ram_total_gb')} GB){bat_str}{disk_str}",
        }

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
                "description": "Control the PC. Valid commands: open <app/shortcut/Store app/game/folder/file/settings/site>, close <app/window>, scan [query], running apps, minimize/maximize/restore [window], show desktop, switch window, snap left/right, new tab, close tab, reopen tab, next/previous tab, fullscreen, refresh, play/pause/next/previous, volume <up/down/mute/0-100>, brightness <up/down/0-100>, screenshot, empty recycle bin, clipboard, ip/wifi, status/battery/cpu/ram/disk, lock/sleep/shutdown/restart, type <text>, press <key_combo>",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "PC command to run"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "close_app",
                "description": "Close an open application window or terminate a running program by name (e.g. 'chrome', 'spotify', 'youtube', 'word', 'active window').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target": {"type": "STRING", "description": "App or window name to close"}
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "window_control",
                "description": "Control desktop windows and browser tabs: minimize, maximize, restore, close, show_desktop, snap_left, snap_right, switch, task_view, focus, new_tab, close_tab, reopen_tab, next_tab, prev_tab, refresh, fullscreen, zoom_in, zoom_out.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "Window or tab action"},
                        "target": {"type": "STRING", "description": "Optional window title or app name to focus first"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "browser_search",
                "description": "Open a web browser search on Google, YouTube, Spotify, GitHub, Reddit, Amazon, Bing, or Wikipedia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Search query to open"},
                        "engine": {"type": "STRING", "description": "'google' (default), 'youtube', 'spotify', 'github', 'reddit', 'amazon', 'wikipedia', or 'bing'"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "scan_pc",
                "description": "Scan and search the user's PC for installed apps, Desktop/Start Menu/Chrome App shortcuts (.lnk/.url), Microsoft Store/UWP apps (Claude, Instagram, TikTok, Duolingo, Reddit, TradingView, etc.), games, folders, and local files. Can also launch the best match immediately when launch_best=True.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Name or keyword of the app, shortcut, game, folder, or file to search for (leave empty to list installed shortcuts, apps, and desktop items)"},
                        "category": {"type": "STRING", "description": "Filter category: 'all' (default), 'shortcuts', 'apps', 'desktop', 'files', or 'folders'"},
                        "launch_best": {"type": "BOOLEAN", "description": "True to immediately launch/open the top matching shortcut, app, or file; False (default) to only scan and report"}
                    }
                }
            },
            {
                "name": "youtube_control",
                "description": "Open the user's installed YouTube shortcut/app (on Desktop/Chrome Apps) or search for a video, song, or channel inside the YouTube app instead of opening a generic browser tab.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "'open' or 'search'"},
                        "query": {"type": "STRING", "description": "Video, artist, song, or topic to search on YouTube (leave empty to just open the YouTube shortcut app)"}
                    },
                    "required": ["action"]
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
            },
            {
                "name": "click_app_element",
                "description": "Move the mouse naturally to and click (or double_click / right_click / hover) any button, link, tab, chat, menu, or control inside the currently active app window.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "label": {"type": "STRING", "description": "The name, label, or description of the button, tab, link, or item to click (e.g. 'Chats', 'New chat', 'Search', 'Subscriptions', 'Send', 'Settings', 'Profile')"},
                        "app_name": {"type": "STRING", "description": "Optional name of the target app (leave empty to act inside the currently active app)"},
                        "action": {"type": "STRING", "description": "'click' (default), 'double_click', 'right_click', or 'hover'"}
                    },
                    "required": ["label"]
                }
            },
            {
                "name": "type_into_app",
                "description": "Type or paste text directly into the active app, optionally clicking a specific input/search box first.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "The text to type or paste into the app"},
                        "element_label": {"type": "STRING", "description": "Optional label of the text field / search box to click first before typing"},
                        "app_name": {"type": "STRING", "description": "Optional app name (leave empty to type in current active app)"},
                        "press_enter": {"type": "BOOLEAN", "description": "Whether to press Enter after typing (default False)"},
                        "clear_first": {"type": "BOOLEAN", "description": "Whether to select-all and clear existing text first (default False)"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "app_navigate",
                "description": "Navigate and move freely inside the active app: scroll down/up, page down/up, home/end, back/forward, refresh, tab, enter, escape, save, undo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "Action: 'scroll_down', 'scroll_up', 'page_down', 'page_up', 'home', 'end', 'back', 'forward', 'refresh', 'tab', 'enter', 'escape', 'save', 'undo'"},
                        "amount": {"type": "INTEGER", "description": "Number of scroll/page increments (default 1)"},
                        "app_name": {"type": "STRING", "description": "Optional app name"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "in_app_search",
                "description": "Trigger in-app search inside whatever app the user is working in and enter a search query.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Search query to enter into the app's search bar"},
                        "app_name": {"type": "STRING", "description": "Optional app name"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "describe_current_app",
                "description": "Identify what application and window the user is currently inside and list visible interactive controls.",
                "parameters": {"type": "OBJECT", "properties": {}}
            }
        ]
    }
]

FAST_MODEL = "gemini-3.1-flash-lite"
SMART_MODEL = "gemini-3-flash-preview"
HISTORY_TURNS = 8
REQUEST_TIMEOUT = (3.5, 10)    # (connect, read) seconds per HTTP call
TOTAL_DEADLINE_SEC = 18        # fast cap across retries/fallbacks
_HTTP_SESSION = requests.Session()

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
    """Keep thinking low so replies come back fast."""
    if "lite" in model:
        return None
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
        if fn_name == "click_app_element":
            res = ace_actions.click_app_element(
                label=fn_args.get("label", ""),
                app_name=fn_args.get("app_name"),
                action=fn_args.get("action", "click"),
            )
            return {"success": True, "result": res}
        if fn_name == "type_into_app":
            res = ace_actions.type_into_app(
                text=fn_args.get("text", ""),
                element_label=fn_args.get("element_label"),
                app_name=fn_args.get("app_name"),
                press_enter=bool(fn_args.get("press_enter", False)),
                clear_first=bool(fn_args.get("clear_first", False)),
            )
            return {"success": True, "result": res}
        if fn_name == "app_navigate":
            res = ace_actions.app_navigate(
                action=fn_args.get("action", "scroll_down"),
                app_name=fn_args.get("app_name"),
                amount=int(fn_args.get("amount", 1)),
            )
            return {"success": True, "result": res}
        if fn_name == "in_app_search":
            res = ace_actions.in_app_search(
                query=fn_args.get("query", ""),
                app_name=fn_args.get("app_name"),
            )
            return {"success": True, "result": res}
        if fn_name == "describe_current_app":
            res = ace_actions.describe_current_app()
            return {"success": True, "result": res}
        if fn_name == "close_app":
            return {"success": True, "result": ace_actions.close_app(fn_args.get("target", ""))}
        if fn_name == "window_control":
            return {
                "success": True,
                "result": ace_actions.window_control(
                    action=fn_args.get("action", ""),
                    target=fn_args.get("target", ""),
                ),
            }
        if fn_name == "browser_search":
            return {
                "success": True,
                "result": ace_actions.browser_search(
                    query=fn_args.get("query", ""),
                    engine=fn_args.get("engine", "google"),
                ),
            }
        if fn_name == "scan_pc":
            return ace_actions.scan_pc(
                query=fn_args.get("query", ""),
                category=fn_args.get("category", "all"),
                launch_best=bool(fn_args.get("launch_best", False)),
            )
        if fn_name == "youtube_control":
            res = ace_actions.youtube_control(
                action=fn_args.get("action", "open"),
                query=fn_args.get("query", ""),
            )
            return {"success": True, "result": res}
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

    # Automatically upgrade deprecated/overloaded model names from old settings
    if model in ("gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"):
        model = FAST_MODEL

    user_name = ace_config.get_user_name()
    profile = ace_config.get_profile()
    slang = ", ".join(profile.get("learnedWords", ["bet", "say less", "let's cook"]))
    style = profile.get("speechStyle", "casual_bro")
    mem = ace_config.get_memory()
    facts = "; ".join(mem.get("facts", [])) or "none yet"

    active_app = ace_actions.get_active_app_context()
    act_name = active_app.get("app_name") or "Desktop"
    act_title = active_app.get("title") or "Desktop"
    act_proc = active_app.get("process_name") or "explorer.exe"

    sys_prompt = (
        f"You are Ace, a sharp, loyal, witty, and confident AI desktop companion (like Jarvis with street-smarts). "
        f"You have full liberty and unrestricted control over this PC and inside applications as {user_name}'s Jarvis. "
        f"CURRENT ACTIVE APP ON SCREEN: {act_name} (Window title: '{act_title}', Process: {act_proc}). "
        f"You know what app {user_name} is in at all times. You can move freely, see, and touch/click controls, buttons, links, tabs, and input boxes inside {act_name} as if it was you moving and working in that space using click_app_element, type_into_app, app_navigate, in_app_search, and describe_current_app. "
        f"When {user_name} asks to click on something ('click on X', 'select Y', 'touch Z'), type something, scroll, search, or asks what app they are in, you are acting DIRECTLY inside {act_name} without asking which app they mean. "
        f"You can also scan {user_name}'s PC for installed apps, Desktop/Start Menu/Chrome App shortcuts (.lnk/.url), Microsoft Store apps, games, folders, and local files using scan_pc, "
        f"launch any shortcut, Store app, program, settings page, or file using execute_pc_command('open <name>'), close apps using close_app, and manage windows/tabs using window_control — NEVER assume only browser apps exist. "
        f"When {user_name} asks to open YouTube or search/play something on YouTube, ALWAYS call youtube_control so it uses their installed YouTube shortcut app instead of a generic browser tab. "
        f"When {user_name} asks what apps, shortcuts, games, or files they have installed, or asks you to scan/search their PC for something, ALWAYS call scan_pc. "
        f"When {user_name} asks to write an essay, speech, greeting, letter, or text in Word or Notepad, ALWAYS call write_document with the complete, well-written text in 'content'. "
        f"When {user_name} asks to text/message someone on WhatsApp, ALWAYS call send_whatsapp_message with the contact name/number and message. "
        f"When {user_name} asks to play or control music on Spotify, call spotify_control. "
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
        for step in range(4):
            if _time.monotonic() > deadline:
                last_error = "took too long"
                break
            gen_cfg: Dict[str, Any] = {"temperature": 0.7}
            if thinking:
                gen_cfg["thinkingConfig"] = thinking
            payload = {
                "systemInstruction": {"parts": [{"text": sys_prompt}]},
                "contents": contents,
                "tools": GEMINI_TOOLS_DECLARATION,
                "generationConfig": gen_cfg,
            }

            try:
                resp = _HTTP_SESSION.post(
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
                    _time.sleep(0.4)
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
        return "Tell me to open any app, shortcut, game, or folder, close apps, control windows/tabs, play YouTube or Spotify, adjust volume/brightness, screenshot, or ask me anything."
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

    # Instant answers & direct PC commands that don't need a cloud round-trip (<15ms latency)
    fast = _fast_local_reply(clean)
    if fast:
        ace_config.add_memory(clean, fast)
        return {"reply": fast}

    settings = ace_config.get_settings()
    api_key = settings.get("aiApiKey") or os.environ.get("GEMINI_API_KEY")
    model = settings.get("aiModel") or FAST_MODEL

    # Try Gemini if key available
    api_error = None
    if api_key:
        result = invoke_gemini(clean, api_key, model=model)
        if result.get("reply"):
            ace_config.add_memory(clean, result["reply"])
            return result
        api_error = result.get("error")
        print(f"[AceBrain] Gemini failed: {api_error}")

    # Fallback to local execution
    cmd_res = execute_pc_command(clean)
    if cmd_res.get("success"):
        reply = cmd_res.get("result", "")
        ace_config.add_memory(clean, reply)
        return {"reply": reply}

    if api_error:
        return {"reply": "My brain's connection is lagging right now, bro. Hit me again in a sec.",
                "error": api_error}

    reply = get_local_reply(clean)
    ace_config.add_memory(clean, reply)
    return {"reply": reply}


_TIME_RE = re.compile(r"^(what('?s| is) the time|what time is it|time\??|que horas s[aã]o)\??$")
_DATE_RE = re.compile(r"^(what('?s| is) (the date|today('?s date)?)|what day is (it|today)|date\??)\??$")


def _fast_local_reply(text: str) -> Optional[str]:
    """Execute unambiguous single-step PC commands locally in <15ms without waiting for LLM network latency."""
    raw = text.strip()
    t = re.sub(r"[!.?]+$", "", raw.lower().strip())
    n = ace_config.get_user_name()

    if _TIME_RE.match(t):
        return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}, {n}."
    if _DATE_RE.match(t):
        return f"Today is {datetime.now().strftime('%A, %B %d')}, {n}."

    # Let Gemini handle multi-step or creative commands ("open word and write an essay...", "send whatsapp message to...")
    if any(sep in f" {t} " for sep in (" and ", " e ", " then ", " write ", " essay ", " speech ", " whatsapp ", " message to ", " text to ")):
        return None

    # 1. Open / Launch / Start / Run <target>
    m_open = re.match(
        r"^(?:can\s+you\s+|please\s+)?(?:open|launch|start|run|abre|abrir|iniciar)\s+(?:up\s+)?(.+?)(?:\s+please|\s+for\s+me|\s+por\s+favor)?$",
        raw,
        flags=re.IGNORECASE,
    )
    if m_open:
        target_raw = m_open.group(1).strip().rstrip(".!?")
        key, prefer_kind, _ = ace_actions._clean_open_query(target_raw)
        if key in ("new tab", "a new tab"):
            return ace_actions.window_control("new_tab")
        if any(sep in f" {key} " for sep in (" search ", " pesquise ", " play ")):
            return None
        known = (
            key in getattr(ace_actions, "APP_ALIASES", {})
            or key in getattr(ace_actions, "WEB_FALLBACKS", {})
            or bool(re.search(r"\.\w{2,4}$|^https?://", key))
            or (ace_actions.find_pc_item(key, min_score=68.0, prefer_kind=prefer_kind) is not None)
        )
        if known:
            return ace_actions.open_target(target_raw)
        return None

    # 2. Direct PC commands (close, window control, media, youtube/spotify/google search, volume, brightness, status, scan, power, etc.)
    direct_res = execute_pc_command(raw)
    if direct_res.get("success"):
        return str(direct_res.get("result", "Done."))

    return None



