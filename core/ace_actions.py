"""
Ace PC Actions Engine - Desktop automation and system control
"""
import os
import sys
import time
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import pyautogui
    # Configure pyautogui failsafe
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

APP_ALIASES = {
    "downloads": os.path.expanduser("~/Downloads"),
    "documents": os.path.expanduser("~/Documents"),
    "desktop": os.path.expanduser("~/Desktop"),
    "pictures": os.path.expanduser("~/Pictures"),
    "music": os.path.expanduser("~/Music"),
    "videos": os.path.expanduser("~/Videos"),
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "browser": "https://www.google.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "netflix": "https://www.netflix.com",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "spotify": "spotify:",
    "discord": "discord:",
    "whatsapp": "whatsapp:",
    "steam": "steam:",
    "store": "ms-windows-store:",
    "camera": "microsoft.windows.camera:",
    "snipping tool": "ms-screenclip:",
}

def type_text(text: str, delay_ms: int = 15) -> None:
    if not text or not pyautogui:
        return
    interval = max(0.005, delay_ms / 1000.0)
    pyautogui.write(text, interval=interval)

def send_key_combo(combo: str) -> None:
    if not pyautogui or not combo:
        return
    c = combo.strip().lower()
    mapping = {
        "enter": ["enter"],
        "tab": ["tab"],
        "copy": ["ctrl", "c"],
        "paste": ["ctrl", "v"],
        "cut": ["ctrl", "x"],
        "select all": ["ctrl", "a"],
        "save": ["ctrl", "s"],
        "undo": ["ctrl", "z"],
        "redo": ["ctrl", "y"],
        "new tab": ["ctrl", "t"],
        "close tab": ["ctrl", "w"],
        "escape": ["esc"],
        "close window": ["alt", "f4"],
        "refresh": ["f5"],
        "find": ["ctrl", "f"]
    }
    keys = mapping.get(c, [c])
    pyautogui.hotkey(*keys)

def open_target(target: str) -> str:
    if not target or not target.strip():
        return "Open what, bro?"
    t = target.strip().strip('"').rstrip('.!?')
    key = t.lower()
    for prefix in ["the ", "my ", "up "]:
        if key.startswith(prefix):
            key = key[len(prefix):]
    for suffix in [" app", " application", " for me", " please"]:
        if key.endswith(suffix):
            key = key[:-len(suffix)]

    if key in APP_ALIASES:
        t = APP_ALIASES[key]

    # Check for web address
    if any(t.endswith(ext) for ext in [".com", ".org", ".net", ".io", ".dev", ".ai", ".co", ".app", ".tv", ".gg"]):
        if not t.startswith("http://") and not t.startswith("https://"):
            t = f"https://{t}"

    if t.startswith("http://") or t.startswith("https://"):
        webbrowser.open(t)
        return f"Opened {target} in browser."

    # Windows shell execute
    try:
        os.startfile(t)
        return f"Opened {target}."
    except Exception:
        pass

    # Try subprocess run
    try:
        subprocess.Popen(t, shell=True)
        return f"Opened {target}."
    except Exception as e:
        return f"Couldn't launch '{target}': {e}"

def set_volume(action: str, steps: int = 5) -> str:
    if not pyautogui:
        return "Audio controls unavailable."
    act = action.lower()
    if act == "mute":
        pyautogui.press("volumemute")
        return "Muted audio."
    elif act == "down":
        for _ in range(steps):
            pyautogui.press("volumedown")
        return f"Turned volume down {steps} steps."
    elif act == "up":
        for _ in range(steps):
            pyautogui.press("volumeup")
        return f"Turned volume up {steps} steps."
    return "Unknown volume command."

def take_screenshot() -> str:
    pictures_dir = Path(os.path.expanduser("~/Pictures"))
    pictures_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = pictures_dir / f"Ace_Screenshot_{stamp}.png"
    
    if ImageGrab:
        img = ImageGrab.grab()
        img.save(str(path))
        return str(path)
    elif pyautogui:
        pyautogui.screenshot(str(path))
        return str(path)
    return "Screenshot tool unavailable."

def get_pc_metrics() -> Dict[str, Any]:
    metrics = {"cpu": "?", "ram_used_gb": 0, "ram_total_gb": 0, "ram_percent": 0, "battery": None}
    try:
        import psutil
        vm = psutil.virtual_memory()
        metrics["ram_used_gb"] = round(vm.used / (1024**3), 1)
        metrics["ram_total_gb"] = round(vm.total / (1024**3), 1)
        metrics["ram_percent"] = vm.percent
        metrics["cpu"] = psutil.cpu_percent(interval=0.1)
        bat = psutil.sensors_battery()
        if bat:
            metrics["battery"] = int(bat.percent)
    except ImportError:
        # Fallback via PowerShell CIM instance if psutil not installed
        try:
            cmd = "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | ConvertTo-Json"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], text=True)
            import json
            data = json.loads(out)
            total = round(data["TotalVisibleMemorySize"] / (1024 * 1024), 1)
            free = round(data["FreePhysicalMemory"] / (1024 * 1024), 1)
            used = round(total - free, 1)
            metrics["ram_total_gb"] = total
            metrics["ram_used_gb"] = used
            metrics["ram_percent"] = round((used / total) * 100) if total else 0
        except Exception:
            pass
    return metrics
