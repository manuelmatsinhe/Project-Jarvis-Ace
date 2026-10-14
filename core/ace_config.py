"""
Ace Configuration and Memory Management
Handles settings.json, profile.json, and memory.json
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_PATH = CONFIG_DIR / "settings.json"
PROFILE_PATH = CONFIG_DIR / "profile.json"
MEMORY_PATH = CONFIG_DIR / "memory.json"

DEFAULT_SETTINGS = {
    "corner": "TR",
    "theme": "cyber_dark",
    "alwaysOnTop": True,
    "voiceEnabled": False,
    "soundFeedback": True,
    "typingDelayMs": 30,
    "wakeWord": "ace",
    "autoNudgeIntervalSec": 120,
    "displayMode": "block",
    "nudgeMinutes": 20,
    "aiModel": "gemini-3.5-flash",
}

DEFAULT_PROFILE = {
    "userName": "Bro",
    "speechStyle": "casual_bro",
    "learnedWords": ["bet", "say less", "let's cook"]
}

DEFAULT_MEMORY = {
    "facts": [],
    "history": []
}

def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        save_json(path, default)
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            # Ensure defaults are populated
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"[AceConfig] Error loading {path.name}: {e}")
        return dict(default)

def save_json(path: Path, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[AceConfig] Error saving {path.name}: {e}")
        return False

# --- Settings ---
def get_settings() -> Dict[str, Any]:
    return load_json(SETTINGS_PATH, DEFAULT_SETTINGS)

def save_settings(settings: Dict[str, Any]) -> bool:
    return save_json(SETTINGS_PATH, settings)

def get_setting(key: str, default: Any = None) -> Any:
    return get_settings().get(key, default)

def set_setting(key: str, value: Any) -> bool:
    s = get_settings()
    s[key] = value
    return save_settings(s)

# --- Profile ---
def get_profile() -> Dict[str, Any]:
    return load_json(PROFILE_PATH, DEFAULT_PROFILE)

def save_profile(profile: Dict[str, Any]) -> bool:
    return save_json(PROFILE_PATH, profile)

def get_user_name() -> str:
    p = get_profile()
    return p.get("userName") or "Bro"

def add_learned_word(word: str) -> None:
    p = get_profile()
    words = p.get("learnedWords", [])
    if word.lower() not in [w.lower() for w in words]:
        words.append(word)
        p["learnedWords"] = words
        save_profile(p)

# --- Memory ---
def get_memory() -> Dict[str, Any]:
    return load_json(MEMORY_PATH, DEFAULT_MEMORY)

def save_memory(mem: Dict[str, Any]) -> bool:
    return save_json(MEMORY_PATH, mem)

def add_memory(user_msg: str, ace_reply: str) -> None:
    mem = get_memory()
    history = mem.get("history", [])
    history.append({"user": user_msg, "ace": ace_reply})
    # Keep last 50 interactions
    if len(history) > 50:
        history = history[-50:]
    mem["history"] = history
    save_memory(mem)

def add_fact(fact: str) -> None:
    mem = get_memory()
    facts = mem.get("facts", [])
    if fact not in facts:
        facts.append(fact)
        mem["facts"] = facts
        save_memory(mem)
