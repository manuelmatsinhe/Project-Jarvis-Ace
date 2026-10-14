"""
Ace PC Actions Engine - Complete Computer Control & Automation
Gives Ace full liberty on the PC:
- Keystrokes, shortcuts, hotkeys, text typing
- Mouse movements, clicks, double-clicks, dragging, scrolling
- Shell execution (PowerShell / CMD / scripts)
- Window & Application management
- System settings (volume, screenshot, lock)
"""
import os
import sys
import time
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

try:
    import pyautogui
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

# --- Keyboard Actions ---

def type_text(text: str, delay_ms: int = 15) -> str:
    """Type text simulating human or rapid keystrokes."""
    if not text or not pyautogui:
        return "Cannot type: text empty or pyautogui missing."
    interval = max(0.005, delay_ms / 1000.0)
    pyautogui.write(text, interval=interval)
    return f"Typed: '{text}'"

def press_key(key: str) -> str:
    """Press a single key (e.g., enter, space, esc, backspace)."""
    if not pyautogui:
        return "PyAutoGUI not available."
    k = key.strip().lower()
    pyautogui.press(k)
    return f"Pressed '{k}'"

def hotkey(*keys) -> str:
    """Simulate key combinations (e.g. 'ctrl', 'c' or 'win', 'd')."""
    if not pyautogui:
        return "PyAutoGUI not available."
    cleaned = [k.strip().lower() for k in keys if k]
    pyautogui.hotkey(*cleaned)
    return f"Triggered shortcut: {'+'.join(cleaned)}"

# --- Mouse Actions ---

def move_mouse(x: int, y: int, duration: float = 0.2) -> str:
    """Move cursor smoothly to coordinates (x, y)."""
    if not pyautogui:
        return "PyAutoGUI not available."
    pyautogui.moveTo(x, y, duration=duration)
    return f"Moved mouse to ({x}, {y})"

def click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> str:
    """Click mouse button at current or specified position."""
    if not pyautogui:
        return "PyAutoGUI not available."
    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return f"Clicked {button} at ({x}, {y}) {clicks} time(s)"
    else:
        pyautogui.click(button=button, clicks=clicks)
        return f"Clicked {button} {clicks} time(s)"

def right_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
    """Right-click at position."""
    return click(x, y, button="right")

def double_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
    """Double-click at position."""
    return click(x, y, button="left", clicks=2)

def drag_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """Drag mouse with left button held down to (x, y)."""
    if not pyautogui:
        return "PyAutoGUI not available."
    pyautogui.dragTo(x, y, duration=duration, button='left')
    return f"Dragged mouse to ({x}, {y})"

def scroll(amount: int) -> str:
    """Scroll wheel: positive = up, negative = down."""
    if not pyautogui:
        return "PyAutoGUI not available."
    pyautogui.scroll(amount)
    dir_str = "up" if amount > 0 else "down"
    return f"Scrolled {dir_str} by {abs(amount)}"

def get_mouse_position() -> Tuple[int, int]:
    """Get current mouse cursor coordinates."""
    if not pyautogui:
        return (0, 0)
    pos = pyautogui.position()
    return (pos.x, pos.y)

def get_screen_size() -> Tuple[int, int]:
    """Get resolution (width, height) of primary monitor."""
    if not pyautogui:
        return (1920, 1080)
    size = pyautogui.size()
    return (size.width, size.height)

# --- System & Shell Execution ---

def run_shell(command: str) -> str:
    """Execute raw PowerShell or CMD command on the system with full liberty."""
    if not command or not command.strip():
        return "No command provided."
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        if err and not out:
            return f"Error: {err}"
        return out or "Command executed successfully (no output)."
    except Exception as e:
        return f"Execution failed: {e}"

def open_target(target: str) -> str:
    """Smart launcher for applications, URLs, or folders."""
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

    # Web URL
    if any(t.endswith(ext) for ext in [".com", ".org", ".net", ".io", ".dev", ".ai", ".co", ".app", ".tv", ".gg"]):
        if not t.startswith("http://") and not t.startswith("https://"):
            t = f"https://{t}"

    if t.startswith("http://") or t.startswith("https://"):
        webbrowser.open(t)
        return f"Opened {target} in browser."

    # Windows native start
    try:
        os.startfile(t)
        return f"Opened {target}."
    except Exception:
        pass

    try:
        subprocess.Popen(t, shell=True)
        return f"Opened {target}."
    except Exception as e:
        return f"Couldn't launch '{target}': {e}"

def set_volume(action: str, steps: int = 5) -> str:
    """Adjust system volume: up, down, mute."""
    if not pyautogui:
        return "Audio controls unavailable."
    act = action.lower().strip()
    if act == "mute":
        pyautogui.press("volumemute")
        return "Toggled mute."
    elif act == "down":
        for _ in range(steps):
            pyautogui.press("volumedown")
        return f"Turned volume down {steps} steps."
    elif act == "up":
        for _ in range(steps):
            pyautogui.press("volumeup")
        return f"Turned volume up {steps} steps."
    return "Unknown volume action."

def take_screenshot() -> str:
    """Capture full screen and save to Pictures folder."""
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

def lock_workstation() -> str:
    """Lock the Windows desktop session."""
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked."
    except Exception as e:
        return f"Lock failed: {e}"

def get_pc_metrics() -> Dict[str, Any]:
    """Retrieve live CPU, RAM, and Battery percentages."""
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
