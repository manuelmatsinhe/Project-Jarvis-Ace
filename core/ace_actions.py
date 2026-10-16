"""
Ace PC Actions Engine - Complete Computer Control & In-App Automation
Gives Ace full liberty on the PC and inside applications:
- In-app automation for Microsoft Word (essays, speeches, letters via RTF + direct launch)
- In-app automation for WhatsApp Desktop (search contact, paste message, send)
- In-app automation for Spotify (search & play tracks/playlists, media keys)
- Universal window focus + instant Unicode clipboard paste (Ctrl+V) for any app
- Keystrokes, shortcuts, hotkeys, mouse control, PowerShell execution, system status
"""
import os
import re
import sys
import time
import shutil
import ctypes
import subprocess
import urllib.parse
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

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _find_exe(candidates: List[str], fallback: str) -> str:
    for c in candidates:
        expanded = os.path.expandvars(os.path.expanduser(c))
        if os.path.isfile(expanded):
            return expanded
        w = shutil.which(expanded)
        if w:
            return w
    return fallback


WORD_EXE = _find_exe([
    r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
    "winword.exe",
], "winword.exe")

EXCEL_EXE = _find_exe([
    r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
    "excel.exe",
], "excel.exe")

POWERPNT_EXE = _find_exe([
    r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
    "powerpnt.exe",
], "powerpnt.exe")

CHROME_EXE = _find_exe([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    "chrome.exe",
], "chrome.exe")

EDGE_EXE = _find_exe([
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "msedge.exe",
], "msedge.exe")

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
    "chrome": CHROME_EXE,
    "google chrome": CHROME_EXE,
    "edge": EDGE_EXE,
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
    "word": WORD_EXE,
    "microsoft word": WORD_EXE,
    "excel": EXCEL_EXE,
    "powerpoint": POWERPNT_EXE,
    "outlook": "outlook.exe",
    "spotify": "spotify:",
    "discord": "discord:",
    "whatsapp": "whatsapp:",
    "steam": "steam:",
    "store": "ms-windows-store:",
    "camera": "microsoft.windows.camera:",
    "snipping tool": "ms-screenclip:",
}


# --- Native Clipboard & Window Focus Helpers ---

def set_clipboard(text: str) -> bool:
    """Copy Unicode text directly to the Windows clipboard via ctypes (zero subprocess lag)."""
    if os.name != "nt":
        return False
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p

    data = (text or "").replace("\r\n", "\n").replace("\n", "\r\n")
    raw = (data + "\0").encode("utf-16-le")

    for _ in range(5):
        if user32.OpenClipboard(None):
            try:
                user32.EmptyClipboard()
                h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
                if not h_mem:
                    return False
                ptr = kernel32.GlobalLock(h_mem)
                if not ptr:
                    return False
                ctypes.memmove(ptr, raw, len(raw))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                return True
            finally:
                user32.CloseClipboard()
        time.sleep(0.03)
    return False


def focus_window(title_keyword: str, timeout: float = 6.0) -> bool:
    """Find a visible top-level window matching title_keyword and bring it to foreground."""
    if os.name != "nt" or not title_keyword:
        return False
    user32 = ctypes.windll.user32
    kw = title_keyword.lower().strip()
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    SW_RESTORE = 9

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matched_hwnd = []

        def _enum_cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            if kw in title and "acehud" not in title:
                matched_hwnd.append(hwnd)
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        if matched_hwnd:
            hwnd = matched_hwnd[0]
            try:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, SW_RESTORE)
                # Tap Alt key state so Windows allows background process to SetForegroundWindow
                user32.keybd_event(0x12, 0, 0, 0)
                user32.SetForegroundWindow(hwnd)
                user32.keybd_event(0x12, 0, 2, 0)
                time.sleep(0.15)
                return True
            except Exception:
                pass
        time.sleep(0.25)
    return False


def paste_text(text: str, press_enter: bool = False) -> str:
    """Paste full Unicode/multi-line text instantly via clipboard + Ctrl+V."""
    if not text:
        return "Nothing to paste."
    if not pyautogui:
        return "PyAutoGUI not available."
    set_clipboard(text)
    time.sleep(0.08)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.12)
    if press_enter:
        pyautogui.press("enter")
    return f"Pasted {len(text)} characters."


# --- Keyboard Actions ---

def type_text(text: str, delay_ms: int = 15) -> str:
    """Type text into the active window. Uses fast Unicode clipboard paste for long or accented text."""
    if not text or not pyautogui:
        return "Cannot type: text empty or pyautogui missing."
    # If text is long, multi-line, or contains non-ASCII accents, paste via clipboard so it's instant & exact
    if len(text) > 25 or "\n" in text or any(ord(c) > 127 for c in text):
        paste_text(text, press_enter=False)
        return f"Typed {len(text)} characters."
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


def send_key_combo(combo: str) -> str:
    """Parse a key combo string like 'ctrl+s', 'alt+tab', or 'enter' and trigger it."""
    if not combo or not pyautogui:
        return "No key combo provided."
    parts = [p.strip().lower() for p in re.split(r"[+\s]+", combo.strip()) if p.strip()]
    if not parts:
        return "No key combo provided."
    if len(parts) == 1:
        return press_key(parts[0])
    return hotkey(*parts)


# --- In-App Automation Actions ---

def _to_rtf_unicode(text: str) -> str:
    """Convert any Unicode string into valid RTF with paragraph breaks."""
    out = []
    for ch in text:
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif ch == "\n":
            out.append("\\par\r\n")
        elif ch == "\r":
            continue
        elif 32 <= code < 127:
            out.append(ch)
        else:
            # RTF signed 16-bit Unicode escape
            signed = code if code < 32768 else code - 65536
            out.append(f"\\u{signed}?")
    return "".join(out)


def write_document(content: str, title: str = "", app: str = "word") -> str:
    """Create and open a formatted document in Microsoft Word (or Notepad) with the given title and content."""
    body = (content or "").strip()
    if not body:
        return "No document content provided."

    docs_dir = Path(os.path.expanduser("~/Documents"))
    docs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\s-]", "", title or "Ace_Document").strip().replace(" ", "_")[:40] or "Ace_Document"

    # Also place the full text on clipboard for convenience
    full_plain = f"{title}\n\n{body}" if title else body
    set_clipboard(full_plain)

    target_app = (app or "word").lower().strip()
    if "notepad" in target_app or not os.path.isfile(WORD_EXE):
        txt_path = docs_dir / f"{safe_title}_{stamp}.txt"
        txt_path.write_text(full_plain, encoding="utf-8")
        subprocess.Popen(["notepad.exe", str(txt_path)])
        focus_window(txt_path.name, timeout=4.0)
        return f"Opened Notepad and wrote '{title or safe_title}' ({len(body.split())} words) saved to {txt_path}."

    # Build a rich, formatted RTF document and open it directly in Microsoft Word
    # Passing the file path + /q skips Word's splash and start screen, opening straight into the editor!
    rtf_title = f"\\pard\\sa240\\b\\fs36 {_to_rtf_unicode(title)}\\b0\\fs24\\par\r\n" if title else ""
    rtf_body = f"\\pard\\sa180\\sl276\\slmult1\\fs24 {_to_rtf_unicode(body)}\\par\r\n"
    rtf_content = (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\nouicompat"
        "{\\fonttbl{\\f0\\fnil\\fcharset0 Calibri;}}"
        "\\viewkind4\\uc1\r\n"
        f"{rtf_title}{rtf_body}}}"
    )
    rtf_path = docs_dir / f"{safe_title}_{stamp}.rtf"
    rtf_path.write_text(rtf_content, encoding="ascii", errors="ignore")

    subprocess.Popen([WORD_EXE, "/q", str(rtf_path)])
    focus_window("Word", timeout=6.0)
    return f"Opened Microsoft Word and wrote '{title or safe_title}' ({len(body.split())} words), saved at {rtf_path}."


def send_whatsapp_message(contact: str, message: str, send: bool = True) -> str:
    """Open WhatsApp Desktop, find the contact (by name or phone number), type the message, and send it."""
    who = (contact or "").strip()
    msg = (message or "").strip()
    if not who:
        return "Who should I message on WhatsApp, bro?"
    if not msg:
        return f"What should I say to {who} on WhatsApp?"
    if not pyautogui:
        return "PyAutoGUI is required for WhatsApp automation."

    # Check if contact is a phone number (+258..., digits)
    digits = re.sub(r"[^\d+]", "", who)
    if len(re.sub(r"\D", "", digits)) >= 7 and re.match(r"^[\d+\s()-]+$", who):
        encoded_msg = urllib.parse.quote(msg)
        clean_phone = re.sub(r"\D", "", digits)
        os.startfile(f"whatsapp://send?phone={clean_phone}&text={encoded_msg}")
        focus_window("WhatsApp", timeout=7.0)
        time.sleep(1.5)
        if send:
            pyautogui.press("enter")
            return f"Sent WhatsApp message to {who}: '{msg}'"
        return f"Prepared WhatsApp message to {who}."

    # Contact is a name: open WhatsApp Desktop, search contact, open chat, paste message, and send
    os.startfile("whatsapp:")
    if not focus_window("WhatsApp", timeout=7.0):
        time.sleep(2.0)
        focus_window("WhatsApp", timeout=3.0)
    else:
        time.sleep(0.9)

    # Focus search bar in WhatsApp Desktop (Ctrl+F), clear it, and paste contact name
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("backspace")
    paste_text(who, press_enter=False)

    # Wait for contact search results to filter, then select first result
    time.sleep(1.1)
    pyautogui.press("down")
    time.sleep(0.15)
    pyautogui.press("enter")

    # Wait for chat message box to become active, then paste and send
    time.sleep(0.65)
    paste_text(msg, press_enter=send)
    if send:
        return f"Sent WhatsApp message to {who}: '{msg}'"
    return f"Typed WhatsApp message to {who} (ready to send)."


def spotify_control(action: str = "play", query: str = "") -> str:
    """Control Spotify playback or search and play a track/artist/playlist."""
    act = (action or "play").lower().strip()
    q = (query or "").strip()

    if not q:
        if act in ("pause", "stop", "resume", "toggle", "play"):
            if pyautogui:
                pyautogui.press("playpause")
            return "Toggled Spotify play/pause."
        if act in ("next", "skip"):
            if pyautogui:
                pyautogui.press("nexttrack")
            return "Skipped to next track."
        if act in ("previous", "prev", "back"):
            if pyautogui:
                pyautogui.press("prevtrack")
            return "Went back to previous track."

    # Search and play a query on Spotify
    encoded = urllib.parse.quote(q)
    os.startfile(f"spotify:search:{encoded}")
    focus_window("Spotify", timeout=6.0)
    time.sleep(2.2)
    if pyautogui:
        # Trigger play on top result
        pyautogui.press("playpause")
    return f"Opened Spotify and searched for '{q}'."


def type_in_app(app_name: str, text: str, press_enter: bool = False, shortcut_before: str = "") -> str:
    """Focus or launch an application, optionally press a shortcut, and paste/type text inside it."""
    app = (app_name or "").strip()
    if app:
        if not focus_window(app, timeout=1.2):
            open_target(app)
            focus_window(app, timeout=5.0)
            time.sleep(0.8)
    if shortcut_before:
        send_key_combo(shortcut_before)
        time.sleep(0.3)
    paste_text(text, press_enter=press_enter)
    return f"Typed into {app or 'active window'}: '{text[:80]}'"


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
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_NO_WINDOW,
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

    # Executable file path (e.g. WINWORD.EXE, chrome.exe)
    if os.path.isfile(t):
        try:
            subprocess.Popen([t])
            return f"Opened {target}."
        except Exception as e:
            return f"Couldn't launch '{target}': {e}"

    # Windows native start (URI schemes like whatsapp:, spotify:, folders)
    try:
        os.startfile(t)
        return f"Opened {target}."
    except Exception:
        pass

    try:
        subprocess.Popen(
            t, shell=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )
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
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                stdin=subprocess.DEVNULL, text=True, creationflags=_NO_WINDOW
            )
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
