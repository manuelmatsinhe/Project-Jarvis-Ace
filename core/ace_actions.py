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
import socket
import ctypes
import difflib
import subprocess
import unicodedata
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

try:
    import winreg
except ImportError:
    winreg = None

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
    # User folders & shell locations
    "downloads": os.path.expanduser("~/Downloads"),
    "documents": os.path.expanduser("~/Documents"),
    "desktop": os.path.expanduser("~/Desktop"),
    "pictures": os.path.expanduser("~/Pictures"),
    "music": os.path.expanduser("~/Music"),
    "videos": os.path.expanduser("~/Videos"),
    "home": os.path.expanduser("~"),
    "user folder": os.path.expanduser("~"),
    "recycle bin": "shell:RecycleBinFolder",
    "trash": "shell:RecycleBinFolder",
    "lixeira": "shell:RecycleBinFolder",
    "startup folder": "shell:startup",
    # Core Windows tools & utilities
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "calculadora": "calc.exe",
    "notepad": "notepad.exe",
    "bloco de notas": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "explorador de arquivos": "explorer.exe",
    "task manager": "taskmgr.exe",
    "gerenciador de tarefas": "taskmgr.exe",
    "control panel": "control.exe",
    "painel de controle": "control.exe",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "services": "services.msc",
    "regedit": "regedit.exe",
    "registry editor": "regedit.exe",
    "system info": "msinfo32.exe",
    "system information": "msinfo32.exe",
    "resource monitor": "resmon.exe",
    "event viewer": "eventvwr.msc",
    "character map": "charmap.exe",
    "on screen keyboard": "osk.exe",
    "magnifier": "magnify.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "snipping tool": "ms-screenclip:",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "alarm": "ms-clock:",
    "alarms": "ms-clock:",
    "timer": "ms-clock:",
    "stopwatch": "ms-clock:",
    "photos": "ms-photos:",
    "store": "ms-windows-store:",
    "microsoft store": "ms-windows-store:",
    "xbox": "xbox:",
    # Windows Settings deep links
    "settings": "ms-settings:",
    "configuracoes": "ms-settings:",
    "wifi settings": "ms-settings:network-wifi",
    "network settings": "ms-settings:network",
    "bluetooth": "ms-settings:bluetooth",
    "bluetooth settings": "ms-settings:bluetooth",
    "sound settings": "ms-settings:sound",
    "audio settings": "ms-settings:sound",
    "microphone settings": "ms-settings:privacy-microphone",
    "display settings": "ms-settings:display",
    "screen settings": "ms-settings:display",
    "night light": "ms-settings:nightlight",
    "windows update": "ms-settings:windowsupdate",
    "updates": "ms-settings:windowsupdate",
    "battery settings": "ms-settings:batterysaver",
    "power settings": "ms-settings:powersleep",
    "storage settings": "ms-settings:storagesense",
    "apps settings": "ms-settings:appsfeatures",
    "installed apps": "ms-settings:appsfeatures",
    "startup apps": "ms-settings:startupapps",
    "theme settings": "ms-settings:personalization-colors",
    "dark mode": "ms-settings:personalization-colors",
    "personalization": "ms-settings:personalization",
    # Installed desktop software & URI protocols
    "chrome": CHROME_EXE,
    "google chrome": CHROME_EXE,
    "edge": EDGE_EXE,
    "microsoft edge": EDGE_EXE,
    "firefox": "firefox.exe",
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
}

# Web fallbacks used ONLY when no matching shortcut (.lnk/.url), installed app, Store app, or local file is found on the PC
WEB_FALLBACKS = {
    "browser": "https://www.google.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "netflix": "https://www.netflix.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "twitch": "https://www.twitch.tv",
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


try:
    if os.name == "nt":
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _ensure_default_desktop():
    """Ensure the current thread is attached to the user's interactive 'Default' desktop."""
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        user32.OpenDesktopW.restype = ctypes.c_void_p
        h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_default:
            user32.SetThreadDesktop(ctypes.c_void_p(h_default))
    except Exception:
        pass


_LAST_ACTIVE_APP: Dict[str, Any] = {
    "hwnd": 0,
    "title": "",
    "app_name": "Desktop",
    "process_name": "explorer.exe",
    "rect": (0, 0, 1920, 1080),
    "ts": 0.0,
}


def update_last_active_app(
    hwnd: int,
    title: str = "",
    process_name: str = "",
    rect: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """Record the user's active application whenever the foreground window changes."""
    global _LAST_ACTIVE_APP
    if not hwnd:
        return
    t_clean = (title or "").strip()
    p_clean = (process_name or "").lower().strip()
    if "acehud" in t_clean.lower() or "ace" == p_clean or "program manager" in t_clean.lower():
        return
    friendly = _clean_app_friendly_name(t_clean, p_clean)
    _LAST_ACTIVE_APP = {
        "hwnd": hwnd,
        "title": t_clean,
        "app_name": friendly,
        "process_name": p_clean,
        "rect": rect,
        "ts": time.monotonic(),
    }


def _clean_app_friendly_name(title: str, process_name: str) -> str:
    """Return a clean human-readable application name from window title and process name."""
    t_low = title.lower()
    p_low = process_name.lower()
    if "whatsapp" in t_low or "whatsapp" in p_low:
        return "WhatsApp"
    if "youtube" in t_low:
        return "YouTube"
    if "spotify" in t_low or "spotify" in p_low:
        return "Spotify"
    if "settings" in t_low or "systemsettings" in p_low:
        return "Settings"
    if "chrome" in p_low:
        return "Chrome"
    if "msedge" in p_low:
        return "Edge"
    if "opera" in p_low:
        return "Opera GX" if "gx" in p_low else "Opera"
    if "code" in p_low:
        return "VS Code"
    if "discord" in p_low:
        return "Discord"
    if "steam" in p_low:
        return "Steam"
    if "winword" in p_low:
        return "Microsoft Word"
    if "excel" in p_low:
        return "Microsoft Excel"
    if "powerpnt" in p_low:
        return "PowerPoint"
    if "notepad" in p_low:
        return "Notepad"
    if "claude" in t_low or "claude" in p_low:
        return "Claude"
    if "tradingview" in t_low or "tradingview" in p_low:
        return "TradingView"
    if "dead space" in t_low:
        return "Dead Space"
    if "hoop land" in t_low:
        return "Hoop Land"
    if "tlauncher" in t_low or "tlauncher" in p_low:
        return "TLauncher"
    if title:
        parts = re.split(r"\s+[-—|]\s+", title)
        cand = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
        return cand[:30]
    return process_name.replace(".exe", "").title() if process_name else "Desktop"


def get_active_app_context() -> Dict[str, Any]:
    """Return live info about the application/window the user is currently inside."""
    _ensure_default_desktop()
    if os.name != "nt":
        return dict(_LAST_ACTIVE_APP)

    user32 = ctypes.windll.user32
    from ctypes import wintypes
    import psutil

    def _inspect_hwnd(h: int) -> Optional[Dict[str, Any]]:
        if not h or not user32.IsWindow(h) or not user32.IsWindowVisible(h):
            return None
        length = user32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h, buf, length + 1)
        title = buf.value.strip()
        if not title or "acehud" in title.lower() or title.lower() in ("program manager", "windows input experience"):
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        pname = ""
        try:
            pname = psutil.Process(pid.value).name()
        except Exception:
            pass
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        w = rect.right - rect.left
        h_h = rect.bottom - rect.top
        if w < 120 or h_h < 80:
            return None
        friendly = _clean_app_friendly_name(title, pname)
        return {
            "hwnd": h,
            "title": title,
            "app_name": friendly,
            "process_name": pname,
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
            "width": w,
            "height": h_h,
            "is_minimized": bool(user32.IsIconic(h)),
        }

    # 1. Try currently active foreground window
    fg_hwnd = user32.GetForegroundWindow()
    fg_info = _inspect_hwnd(fg_hwnd)
    if fg_info:
        update_last_active_app(fg_info["hwnd"], fg_info["title"], fg_info["process_name"], fg_info["rect"])
        return fg_info

    # 2. If foreground window is AceHUD or null, use fresh _LAST_ACTIVE_APP if valid
    if _LAST_ACTIVE_APP["hwnd"] and (time.monotonic() - _LAST_ACTIVE_APP["ts"] < 15.0):
        if user32.IsWindow(_LAST_ACTIVE_APP["hwnd"]) and user32.IsWindowVisible(_LAST_ACTIVE_APP["hwnd"]):
            return dict(_LAST_ACTIVE_APP)

    # 3. Fallback: inspect top-most visible application window in Z-order
    top_match = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _enum_cb(h, _):
        nonlocal top_match
        info = _inspect_hwnd(h)
        if info and not info["is_minimized"]:
            top_match = info
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
    if top_match:
        update_last_active_app(top_match["hwnd"], top_match["title"], top_match["process_name"], top_match["rect"])
        return top_match

    return dict(_LAST_ACTIVE_APP)


def focus_active_app(target: Optional[str] = None) -> bool:
    """Bring the active user app (or a specific target app) to the foreground."""
    _ensure_default_desktop()
    if os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    SW_RESTORE = 9

    if target and target.strip():
        return focus_window(target.strip(), timeout=2.0)

    app = get_active_app_context()
    hwnd = app.get("hwnd", 0)
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.keybd_event(0x12, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.08)
        return True
    except Exception:
        return False


# UIAutomation cache request and singleton
_UIA_INSTANCE = None


def _get_uia():
    global _UIA_INSTANCE
    if _UIA_INSTANCE is None and os.name == "nt":
        try:
            import comtypes.client
            uia = comtypes.client.GetModule("UIAutomationCore.dll")
            auto = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=uia.IUIAutomation)
            _UIA_INSTANCE = (auto, uia)
        except Exception:
            _UIA_INSTANCE = False
    return _UIA_INSTANCE if _UIA_INSTANCE else None


def get_app_ui_elements(target_app: Optional[str] = None, max_elements: int = 60) -> List[Dict[str, Any]]:
    """Scan and return interactive UI elements (buttons, links, inputs, tabs, menus) from the active app window."""
    _ensure_default_desktop()
    if target_app:
        focus_window(target_app, timeout=1.5)

    app = get_active_app_context()
    hwnd = app.get("hwnd", 0)
    if not hwnd:
        return []

    uia_tuple = _get_uia()
    if not uia_tuple:
        return []

    auto, uia = uia_tuple
    user32 = ctypes.windll.user32

    # Collect top window and visible child content windows (for WebView2/Chromium/UWP)
    hwnds_to_check = [hwnd]
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _child_cb(ch, _):
        if user32.IsWindowVisible(ch):
            hwnds_to_check.append(ch)
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(_child_cb), 0)

    cache_req = auto.CreateCacheRequest()
    cache_req.AddProperty(30005)  # Name
    cache_req.AddProperty(30003)  # ControlType
    cache_req.AddProperty(30001)  # BoundingRectangle

    # Interactive controls: Button(50000), Edit(50004), Hyperlink(50005), MenuItem(50011), TabItem(50019)
    c1 = auto.CreatePropertyCondition(30003, 50000)
    c2 = auto.CreatePropertyCondition(30003, 50004)
    c3 = auto.CreatePropertyCondition(30003, 50005)
    c4 = auto.CreatePropertyCondition(30003, 50011)
    c5 = auto.CreatePropertyCondition(30003, 50019)
    or_cond = auto.CreateOrCondition(c1, auto.CreateOrCondition(c2, auto.CreateOrCondition(c3, auto.CreateOrCondition(c4, c5))))

    elements: List[Dict[str, Any]] = []
    seen = set()

    for h in hwnds_to_check:
        try:
            root = auto.ElementFromHandle(h)
            arr = root.FindAllBuildCache(uia.TreeScope_Descendants, or_cond, cache_req)
            for i in range(arr.Length):
                el = arr.GetElement(i)
                nm = (el.CachedName or "").strip()
                if not nm or nm.lower() in seen or len(nm) > 80:
                    continue
                r = el.CachedBoundingRectangle
                w = r.right - r.left
                h_h = r.bottom - r.top
                if w > 6 and h_h > 6 and r.left >= 0 and r.top >= 0:
                    cx = (r.left + r.right) // 2
                    cy = (r.top + r.bottom) // 2
                    seen.add(nm.lower())
                    elements.append({
                        "label": nm,
                        "x": cx,
                        "y": cy,
                        "width": w,
                        "height": h_h,
                        "control_type": el.CachedControlType,
                    })
                    if len(elements) >= max_elements:
                        break
        except Exception:
            pass
        if len(elements) >= max_elements:
            break

    return elements


def click_app_element(
    label: str,
    app_name: Optional[str] = None,
    action: str = "click",
) -> str:
    """Move naturally to and click (or double_click / right_click / hover) a button, link, tab, or element in the active app."""
    target_clean = (label or "").strip()
    if not target_clean:
        return "Click what element, bro?"

    _ensure_default_desktop()
    focus_active_app(app_name)

    app = get_active_app_context()
    app_display = app.get("app_name") or "this app"
    low_target = target_clean.lower()

    # 1. Search UIAutomation elements in the active app
    elements = get_app_ui_elements(target_app=app_name, max_elements=80)
    best_match = None
    best_score = 0.0

    for el in elements:
        el_label = el["label"].lower()
        if el_label == low_target:
            best_match = el
            best_score = 100.0
            break
        if el_label.startswith(low_target) or low_target in el_label:
            score = 85.0 + (len(low_target) / len(el_label)) * 10
            if score > best_score:
                best_score = score
                best_match = el
        else:
            ratio = difflib.SequenceMatcher(None, low_target, el_label).ratio()
            if ratio >= 0.72 and (ratio * 80) > best_score:
                best_score = ratio * 80
                best_match = el

    if best_match and pyautogui:
        x, y = best_match["x"], best_match["y"]
        matched_label = best_match["label"]
        pyautogui.moveTo(x, y, duration=0.18)
        act = action.lower()
        if act == "double_click":
            pyautogui.doubleClick(x, y)
            return f"Double-clicked '{matched_label}' in {app_display}."
        elif act in ("right_click", "context_menu"):
            pyautogui.rightClick(x, y)
            return f"Right-clicked '{matched_label}' in {app_display}."
        elif act == "hover":
            return f"Moved cursor to '{matched_label}' in {app_display}."
        else:
            pyautogui.click(x, y)
            return f"Clicked '{matched_label}' in {app_display}."

    # 2. Smart keyboard / navigation fallbacks if not in UIAutomation tree
    if any(w in low_target for w in ("search", "find", "search bar", "pesquisar", "busca")):
        if "youtube" in app_display.lower() and pyautogui:
            pyautogui.press("/")
            return f"Focused search bar in {app_display}."
        elif pyautogui:
            pyautogui.hotkey("ctrl", "f")
            return f"Focused search in {app_display}."

    if any(w in low_target for w in ("new", "new chat", "new tab", "nova")):
        if pyautogui:
            pyautogui.hotkey("ctrl", "n")
            return f"Triggered New in {app_display}."

    if any(w in low_target for w in ("play", "pause", "resume", "tocar", "pausar")):
        if pyautogui:
            pyautogui.press("space")
            return f"Toggled play/pause in {app_display}."

    if any(w in low_target for w in ("center", "middle", "video", "screen", "canvas")):
        rect = app.get("rect")
        if rect and pyautogui:
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2
            pyautogui.moveTo(cx, cy, duration=0.18)
            pyautogui.click()
            return f"Clicked center of {app_display}."

    return f"Couldn't find '{target_clean}' in {app_display}. Tell me where to click or what to type."


def type_into_app(
    text: str,
    element_label: Optional[str] = None,
    app_name: Optional[str] = None,
    press_enter: bool = False,
    clear_first: bool = False,
) -> str:
    """Type or paste text directly into the active app, optionally clicking a specific input box first."""
    if not text:
        return "Type what text, bro?"

    _ensure_default_desktop()
    focus_active_app(app_name)

    app = get_active_app_context()
    app_display = app.get("app_name") or "this app"

    if element_label:
        click_app_element(element_label, app_name=app_name, action="click")
        time.sleep(0.1)

    if clear_first and pyautogui:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")

    paste_text(text, press_enter=press_enter)
    dest = f"'{element_label}' in {app_display}" if element_label else app_display
    return f"Typed '{text}' into {dest}."


def app_navigate(action: str, app_name: Optional[str] = None, amount: int = 1) -> str:
    """Move freely inside the active app: scroll, page, home/end, tabs, refresh, back/forward, zoom."""
    _ensure_default_desktop()
    focus_active_app(app_name)

    app = get_active_app_context()
    app_display = app.get("app_name") or "this app"
    act = (action or "").lower().strip().replace(" ", "_")

    if not pyautogui:
        return "Navigation controls unavailable."

    # Move mouse inside the window so scroll events target the app
    rect = app.get("rect")
    if rect:
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        pyautogui.moveTo(cx, cy, duration=0.05)

    times = max(1, min(20, amount))

    if act in ("scroll_down", "down", "descer"):
        pyautogui.scroll(-360 * times)
        return f"Scrolled down in {app_display}."
    elif act in ("scroll_up", "up", "subir"):
        pyautogui.scroll(360 * times)
        return f"Scrolled up in {app_display}."
    elif act in ("page_down", "pagedown"):
        for _ in range(times):
            pyautogui.press("pagedown")
        return f"Paged down in {app_display}."
    elif act in ("page_up", "pageup"):
        for _ in range(times):
            pyautogui.press("pageup")
        return f"Paged up in {app_display}."
    elif act in ("home", "top", "inicio"):
        pyautogui.press("home")
        return f"Jumped to top of {app_display}."
    elif act in ("end", "bottom", "fim"):
        pyautogui.press("end")
        return f"Jumped to bottom of {app_display}."
    elif act in ("back", "voltar"):
        pyautogui.hotkey("alt", "left")
        return f"Navigated back in {app_display}."
    elif act in ("forward", "avancar"):
        pyautogui.hotkey("alt", "right")
        return f"Navigated forward in {app_display}."
    elif act in ("refresh", "reload"):
        pyautogui.press("f5")
        return f"Refreshed {app_display}."
    elif act in ("tab", "next_field"):
        for _ in range(times):
            pyautogui.press("tab")
        return f"Tabbed in {app_display}."
    elif act in ("enter", "return"):
        pyautogui.press("enter")
        return f"Pressed Enter in {app_display}."
    elif act in ("escape", "cancel"):
        pyautogui.press("escape")
        return f"Pressed Escape in {app_display}."
    elif act in ("space", "play_pause"):
        pyautogui.press("space")
        return f"Toggled Space in {app_display}."
    elif act in ("select_all",):
        pyautogui.hotkey("ctrl", "a")
        return f"Selected all in {app_display}."
    elif act in ("copy",):
        pyautogui.hotkey("ctrl", "c")
        return f"Copied to clipboard in {app_display}."
    elif act in ("paste",):
        pyautogui.hotkey("ctrl", "v")
        return f"Pasted in {app_display}."
    elif act in ("save",):
        pyautogui.hotkey("ctrl", "s")
        return f"Saved in {app_display}."
    elif act in ("undo",):
        pyautogui.hotkey("ctrl", "z")
        return f"Undid last action in {app_display}."

    return f"Executed '{action}' in {app_display}."


def in_app_search(query: str, app_name: Optional[str] = None) -> str:
    """Trigger in-app search and enter a search query inside whatever app the user is working in."""
    q = (query or "").strip()
    if not q:
        return "Search for what in this app, bro?"

    _ensure_default_desktop()
    focus_active_app(app_name)

    app = get_active_app_context()
    app_display = app.get("app_name") or "this app"

    if "youtube" in app_display.lower() and pyautogui:
        pyautogui.press("/")
        time.sleep(0.12)
        pyautogui.hotkey("ctrl", "a")
        paste_text(q, press_enter=True)
        return f"Searched for '{q}' in {app_display}."

    # Try finding search input in UIAutomation
    elements = get_app_ui_elements(target_app=app_name, max_elements=40)
    search_el = next((el for el in elements if "search" in el["label"].lower() or "find" in el["label"].lower()), None)
    if search_el and pyautogui:
        pyautogui.moveTo(search_el["x"], search_el["y"], duration=0.15)
        pyautogui.click()
        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "a")
        paste_text(q, press_enter=True)
        return f"Searched for '{q}' in {app_display}."

    if pyautogui:
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "a")
        paste_text(q, press_enter=True)
        return f"Searched for '{q}' in {app_display}."

    return f"Opened search in {app_display} for '{q}'."


def describe_current_app() -> str:
    """Identify the currently active application and summarize what interactive controls are visible."""
    app = get_active_app_context()
    name = app.get("app_name") or "Desktop"
    title = app.get("title") or "No active window"
    elements = get_app_ui_elements(max_elements=30)
    if elements:
        top_labels = [el["label"] for el in elements[:8] if el.get("label")]
        summary = f"You are currently in {name} ('{title}'). Visible clickable controls include: {', '.join(top_labels)}."
    else:
        summary = f"You are currently in {name} ('{title}')."
    return summary


def focus_window(title_keyword: str, timeout: float = 6.0) -> bool:
    """Find a visible top-level window matching title_keyword and bring it to foreground."""
    _ensure_default_desktop()
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


# --- PC Scanner: Shortcuts (.lnk/.url), Installed Apps, Chrome Apps & User Files ---

_PC_CATALOG_CACHE: Dict[str, Any] = {"ts": 0.0, "items": [], "with_files": False, "with_store": False}
_STORE_APPS_CACHE: Dict[str, Any] = {"ts": 0.0, "items": []}

_NOISY_SHORTCUT_WORDS = (
    "uninstall", "desinstalar", "updater", "error reporter", "release notes",
    "faq", "support center", "readme", "help", "manual", "license",
)
_INSTALLER_FILE_WORDS = ("setup", "installer", "install", "inst-", "win64", "x64-setup")


def _normalize_text(text: str) -> str:
    """Accent-insensitive lowercase alphanumeric normalization for fuzzy matching."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", stripped.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _inspect_shortcut(path: Path) -> Dict[str, str]:
    """Fast pure-Python reader for Windows .lnk and .url shortcut files."""
    info: Dict[str, str] = {"target_exe": "", "app_id": "", "profile_dir": "", "url": "", "is_pwa": ""}
    suffix = path.suffix.lower()
    try:
        if suffix == ".url":
            raw_text = path.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^URL=(.+)$", raw_text, flags=re.MULTILINE | re.IGNORECASE)
            if m:
                info["url"] = m.group(1).strip()
            return info
        if suffix != ".lnk":
            return info

        data = path.read_bytes()[:65536]
        utf16_chunks = [
            m.group(0).decode("utf-16le", errors="ignore")
            for m in re.finditer(b"(?:[\x20-\x7e]\x00){4,}", data)
        ]
        ascii_chunks = [
            m.group(0).decode("ascii", errors="ignore")
            for m in re.finditer(b"[\x20-\x7e]{5,}", data)
        ]
        combined = " | ".join(utf16_chunks + ascii_chunks)

        app_id_m = re.search(r"--app-id=([a-zA-Z0-9]{16,40})", combined)
        if app_id_m:
            info["app_id"] = app_id_m.group(1)
            info["is_pwa"] = "true"

        prof_m = re.search(r"--profile-directory=([A-Za-z0-9_ -]+?)(?=\s+--|\||$)", combined)
        if prof_m:
            info["profile_dir"] = prof_m.group(1).strip()

        exe_matches = re.findall(r"[A-Za-z]:\\[^\x00\"|<>?*]+?\.(?:exe|bat|cmd|jar)", combined, flags=re.IGNORECASE)
        if exe_matches:
            # Prefer non-installer target paths that exist on disk
            for cand in exe_matches:
                if os.path.isfile(cand):
                    info["target_exe"] = cand
                    break
            if not info["target_exe"]:
                info["target_exe"] = exe_matches[0]
        elif "chrome_proxy.exe" in combined.lower():
            proxy_cand = Path(CHROME_EXE).parent / "chrome_proxy.exe"
            info["target_exe"] = str(proxy_cand if proxy_cand.is_file() else CHROME_EXE)
    except Exception:
        pass
    return info


def _get_desktop_dirs() -> List[Tuple[str, Path]]:
    dirs: List[Tuple[str, Path]] = []
    seen = set()
    candidates = [
        ("Desktop", Path.home() / "Desktop"),
        ("OneDrive Desktop", Path.home() / "OneDrive" / "Desktop"),
        ("OneDrive Desktop", Path.home() / "OneDrive" / "Ambiente de Trabalho"),
        ("Public Desktop", Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"),
    ]
    for label, p in candidates:
        try:
            resolved = str(p.resolve()).lower()
            if resolved not in seen and p.is_dir():
                seen.add(resolved)
                dirs.append((label, p))
        except Exception:
            pass
    return dirs


def _get_start_menu_dirs() -> List[Tuple[str, Path]]:
    dirs: List[Tuple[str, Path]] = []
    appdata = os.environ.get("APPDATA", "")
    progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    candidates = [
        ("User Start Menu", Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"),
        ("System Start Menu", Path(progdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"),
    ]
    for label, p in candidates:
        if p.is_dir():
            dirs.append((label, p))
    return dirs


_START_APPS_CACHE_FILE = Path(__file__).resolve().parent.parent / "ipc" / "start_apps_cache.json"
_KNOWN_FOLDER_GUIDS = {
    "{6D809377-6AF0-444B-8957-A3773F02200E}": os.environ.get("ProgramW6432", r"C:\Program Files"),
    "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}": os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}": os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32"),
    "{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}": os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64"),
    "{F38BF404-1D43-42F2-9305-67DE0B28FC23}": os.environ.get("WINDIR", r"C:\Windows"),
}


def _resolve_known_folder_appid(app_id: str) -> str:
    """Resolve KnownFolder GUID prefixes in Get-StartApps AppIDs to real filesystem paths when applicable."""
    for guid, folder in _KNOWN_FOLDER_GUIDS.items():
        if app_id.upper().startswith(guid):
            candidate = folder + app_id[len(guid):]
            if os.path.exists(candidate):
                return candidate
    if os.path.exists(app_id):
        return app_id
    return f"shell:AppsFolder\\{app_id}"


def _refresh_start_apps_cache_bg() -> None:
    """Refresh ipc/start_apps_cache.json in a background thread so Ace never blocks on PowerShell."""
    import threading

    def _worker():
        try:
            _START_APPS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            ps_cmd = (
                f"Get-StartApps | ConvertTo-Json -Compress | "
                f"Set-Content -Path '{_START_APPS_CACHE_FILE}' -Encoding UTF8"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                creationflags=_NO_WINDOW,
            )
            _STORE_APPS_CACHE["ts"] = 0.0
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def _scan_store_apps() -> List[Dict[str, Any]]:
    now = time.monotonic()
    if _STORE_APPS_CACHE["items"] and (now - _STORE_APPS_CACHE["ts"] < 300.0):
        return list(_STORE_APPS_CACHE["items"])

    items: List[Dict[str, Any]] = []
    try:
        if _START_APPS_CACHE_FILE.is_file():
            import json
            raw_bytes = _START_APPS_CACHE_FILE.read_bytes()
            text = raw_bytes.decode("utf-8-sig", errors="ignore").strip()
            if text:
                raw = json.loads(text)
                if isinstance(raw, dict):
                    raw = [raw]
                for entry in raw or []:
                    name = (entry.get("Name") or "").strip()
                    app_id = (entry.get("AppID") or "").strip()
                    if not name or not app_id:
                        continue
                    launch_path = _resolve_known_folder_appid(app_id)
                    items.append({
                        "name": name,
                        "kind": "store_app",
                        "location": "Windows Start Apps",
                        "path": launch_path,
                        "app_id": app_id,
                    })
            # Trigger non-blocking refresh if cache is older than 1 hour
            if (time.time() - _START_APPS_CACHE_FILE.stat().st_mtime) > 3600:
                _refresh_start_apps_cache_bg()
        else:
            _refresh_start_apps_cache_bg()
    except Exception:
        pass

    _STORE_APPS_CACHE["ts"] = now
    _STORE_APPS_CACHE["items"] = items
    return items


def scan_pc_catalog(
    force_refresh: bool = False,
    include_files: bool = True,
    include_store_apps: bool = True,
) -> List[Dict[str, Any]]:
    """Scan the PC for Desktop shortcuts, Chrome/PWA app shortcuts, Start Menu apps,
    Taskbar pins, Registry/LocalAppData programs, Windows Store/Start apps, and user files/folders."""
    now = time.monotonic()
    if (
        not force_refresh
        and _PC_CATALOG_CACHE["items"]
        and (now - _PC_CATALOG_CACHE["ts"] < 25.0)
        and (_PC_CATALOG_CACHE["with_files"] or not include_files)
        and (_PC_CATALOG_CACHE["with_store"] or not include_store_apps)
    ):
        return list(_PC_CATALOG_CACHE["items"])

    items: List[Dict[str, Any]] = []
    seen_paths = set()

    def _add(item: Dict[str, Any]):
        p_key = str(item.get("path", "")).lower()
        if not p_key or p_key in seen_paths:
            return
        seen_paths.add(p_key)
        items.append(item)

    # 1. Desktop Shortcuts (.lnk, .url, .appref-ms)
    for label, d_dir in _get_desktop_dirs():
        try:
            for entry in d_dir.iterdir():
                ext = entry.suffix.lower()
                if entry.is_file() and ext in (".lnk", ".url", ".appref-ms"):
                    meta = _inspect_shortcut(entry)
                    _add({
                        "name": entry.stem,
                        "kind": "desktop_shortcut",
                        "location": f"{label} ({ 'Browser App Shortcut' if meta.get('is_pwa') else 'Shortcut' })",
                        "path": str(entry),
                        **meta,
                    })
        except Exception:
            pass

    # 2. Taskbar Pinned Shortcuts
    taskbar_dir = (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
    )
    if taskbar_dir.is_dir():
        try:
            for entry in taskbar_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in (".lnk", ".url", ".appref-ms"):
                    meta = _inspect_shortcut(entry)
                    _add({
                        "name": entry.stem,
                        "kind": "taskbar_shortcut",
                        "location": "Taskbar Pinned",
                        "path": str(entry),
                        **meta,
                    })
        except Exception:
            pass

    # 3. Start Menu Shortcuts (including Chrome Apps / Edge Apps)
    for label, sm_dir in _get_start_menu_dirs():
        try:
            for entry in sm_dir.rglob("*"):
                if not entry.is_file():
                    continue
                ext = entry.suffix.lower()
                if ext not in (".lnk", ".url", ".appref-ms"):
                    continue
                rel_parent = str(entry.parent.relative_to(sm_dir)) if entry.parent != sm_dir else ""
                is_browser_app_folder = any(
                    tag in rel_parent.lower() for tag in ("chrome apps", "edge apps", "brave apps", "opera")
                )
                meta = _inspect_shortcut(entry)
                is_pwa = bool(meta.get("is_pwa")) or is_browser_app_folder
                kind = "chrome_app_shortcut" if is_pwa else "start_menu_shortcut"
                loc = f"Start Menu > {rel_parent}" if rel_parent and rel_parent != "." else label
                _add({
                    "name": entry.stem,
                    "kind": kind,
                    "location": loc,
                    "path": str(entry),
                    **meta,
                })
        except Exception:
            pass

    # 4. Local Installed Programs (%LOCALAPPDATA%\Programs)
    local_progs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"
    if local_progs.is_dir():
        try:
            for sub in local_progs.iterdir():
                if not sub.is_dir():
                    continue
                for exe in sub.glob("*.exe"):
                    stem_l = exe.stem.lower()
                    if any(skip in stem_l for skip in ("unins", "update", "crash", "helper")):
                        continue
                    _add({
                        "name": sub.name if stem_l in ("launcher", "app") else exe.stem,
                        "kind": "installed_app",
                        "location": "Local Programs",
                        "path": str(exe),
                    })
        except Exception:
            pass

    # 5. Windows Registry App Paths & Uninstall Entries (HKCU & HKLM)
    if winreg:
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as root_key:
                    idx = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(root_key, idx)
                            idx += 1
                            with winreg.OpenKey(root_key, sub_name) as app_key:
                                val, _ = winreg.QueryValueEx(app_key, "")
                                if val and isinstance(val, str):
                                    clean_exe = os.path.expandvars(val.strip().strip('"'))
                                    if os.path.isfile(clean_exe):
                                        _add({
                                            "name": Path(sub_name).stem,
                                            "kind": "installed_app",
                                            "location": "Registry App Paths",
                                            "path": clean_exe,
                                        })
                        except OSError:
                            break
            except OSError:
                pass

        for hive, u_path in (
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ):
            try:
                with winreg.OpenKey(hive, u_path) as root_key:
                    idx = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(root_key, idx)
                            idx += 1
                            with winreg.OpenKey(root_key, sub_name) as app_key:
                                try:
                                    disp_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                except OSError:
                                    continue
                                if not disp_name or not isinstance(disp_name, str):
                                    continue
                                exe_cand = ""
                                try:
                                    icon_val, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                    if isinstance(icon_val, str):
                                        cand = os.path.expandvars(icon_val.split(",")[0].strip().strip('"'))
                                        if cand.lower().endswith(".exe") and os.path.isfile(cand):
                                            if not any(w in cand.lower() for w in ("unins", "setup", "installer")):
                                                exe_cand = cand
                                except OSError:
                                    pass
                                if exe_cand:
                                    _add({
                                        "name": disp_name.strip(),
                                        "kind": "installed_app",
                                        "location": "Installed Programs",
                                        "path": exe_cand,
                                    })
                        except OSError:
                            break
            except OSError:
                pass

    # 6. Windows Start / Store Apps (UWP, Microsoft Store apps like Claude, Duolingo, Instagram, TikTok, etc.)
    if include_store_apps:
        for st_item in _scan_store_apps():
            _add(st_item)

    # 7. User Files & Folders (Desktop, Documents, Downloads, Pictures, Music, Videos)
    if include_files:
        user_dirs: List[Tuple[str, Path, bool]] = []
        for label, d_dir in _get_desktop_dirs():
            user_dirs.append((label, d_dir, True))
        for label, folder_name in (
            ("Documents", "Documents"),
            ("Downloads", "Downloads"),
            ("Pictures", "Pictures"),
            ("Music", "Music"),
            ("Videos", "Videos"),
        ):
            p = Path.home() / folder_name
            if p.is_dir():
                user_dirs.append((label, p, False))

        for label, u_dir, is_desk in user_dirs:
            try:
                count = 0
                for entry in u_dir.iterdir():
                    if entry.name.startswith(".") or entry.name.lower() in ("desktop.ini", "thumbs.db"):
                        continue
                    if entry.is_file() and entry.suffix.lower() in (".lnk", ".url", ".appref-ms"):
                        continue
                    count += 1
                    if count > 80:
                        break
                    if entry.is_dir():
                        _add({
                            "name": entry.name,
                            "kind": "desktop_folder" if is_desk else "user_folder",
                            "location": label,
                            "path": str(entry),
                        })
                    elif entry.is_file():
                        _add({
                            "name": entry.name,
                            "stem": entry.stem,
                            "kind": "desktop_file" if is_desk else "user_file",
                            "location": label,
                            "path": str(entry),
                        })
            except Exception:
                pass

    _PC_CATALOG_CACHE["ts"] = now
    _PC_CATALOG_CACHE["items"] = items
    _PC_CATALOG_CACHE["with_files"] = include_files
    _PC_CATALOG_CACHE["with_store"] = include_store_apps
    return list(items)


def _score_pc_item(item: Dict[str, Any], query: str, prefer_kind: str = "") -> float:
    q_norm = _normalize_text(query)
    if not q_norm:
        return 0.0
    q_compact = q_norm.replace(" ", "")
    q_words = q_norm.split()

    name_raw = item.get("stem") or item.get("name") or ""
    item_norm = _normalize_text(name_raw)
    full_norm = _normalize_text(item.get("name") or "")
    if not item_norm:
        return 0.0
    item_compact = item_norm.replace(" ", "")
    item_words = item_norm.split()

    base = 0.0
    if item_norm == q_norm or full_norm == q_norm or (len(q_compact) >= 2 and item_compact == q_compact):
        base = 100.0
    elif item_norm.startswith(q_norm + " ") or full_norm.startswith(q_norm + " "):
        base = 92.0
    elif item_norm.startswith(q_norm) or (len(q_compact) >= 3 and item_compact.startswith(q_compact)):
        base = 86.0
    elif all(w in item_words for w in q_words):
        base = 83.0
    elif len(q_norm) >= 3 and (q_norm in item_norm or q_norm in full_norm):
        base = 75.0
    elif len(q_compact) >= 3 and q_compact in item_compact:
        base = 72.0
    elif len(q_words) > 1 and all(w in item_norm for w in q_words):
        base = 69.0
    else:
        ratio = difflib.SequenceMatcher(None, q_norm, item_norm).ratio()
        word_ratio = max(
            (difflib.SequenceMatcher(None, q_norm, w).ratio() for w in item_words),
            default=0.0,
        ) if len(q_words) == 1 else 0.0
        best_r = max(ratio, word_ratio)
        if best_r >= 0.78:
            base = 62.0 * best_r
        else:
            return 0.0

    kind = item.get("kind", "")
    kind_bonus = {
        "desktop_shortcut": 16.0,
        "chrome_app_shortcut": 14.0,
        "taskbar_shortcut": 13.0,
        "start_menu_shortcut": 11.0,
        "installed_app": 9.0,
        "store_app": 8.5,
        "desktop_folder": 6.0,
        "desktop_file": 5.0,
        "user_folder": 3.0,
        "user_file": 2.0,
    }.get(kind, 1.0)

    score = base + kind_bonus

    if prefer_kind:
        if prefer_kind == "shortcut" and "shortcut" in kind:
            score += 15.0
        elif prefer_kind == "folder" and "folder" in kind:
            score += 18.0
        elif prefer_kind == "file" and "file" in kind:
            score += 18.0
        elif prefer_kind == "app" and kind in ("desktop_shortcut", "chrome_app_shortcut", "start_menu_shortcut", "installed_app", "store_app"):
            score += 10.0

    # Penalize noisy updater/uninstall shortcuts and raw setup installers unless user asked for them
    if any(w in item_norm for w in _NOISY_SHORTCUT_WORDS) and not any(w in q_norm for w in _NOISY_SHORTCUT_WORDS):
        score -= 32.0
    if kind in ("user_file", "desktop_file") and any(w in full_norm for w in _INSTALLER_FILE_WORDS):
        if not any(w in q_norm for w in ("setup", "installer", "install")):
            score -= 28.0

    # Slight preference for cleaner, shorter names on ties
    score -= min(len(item_norm), 50) * 0.05
    return round(score, 2)


def search_pc_items(
    query: str = "",
    category: str = "all",
    limit: int = 25,
    force_refresh: bool = False,
    include_store_apps: bool = True,
    prefer_kind: str = "",
) -> List[Dict[str, Any]]:
    """Search across PC shortcuts, installed apps, Chrome apps, Store apps, and user files/folders."""
    cat = (category or "all").lower().strip()
    catalog = scan_pc_catalog(
        force_refresh=force_refresh,
        include_files=cat not in ("shortcuts", "shortcut", "apps", "programs"),
        include_store_apps=include_store_apps,
    )

    def _category_ok(item: Dict[str, Any]) -> bool:
        k = item.get("kind", "")
        loc = item.get("location", "").lower()
        if cat in ("shortcuts", "shortcut", "atalhos", "atalho"):
            return "shortcut" in k
        if cat in ("apps", "app", "programs", "games", "aplicativos"):
            return k in ("desktop_shortcut", "chrome_app_shortcut", "taskbar_shortcut", "start_menu_shortcut", "installed_app", "store_app")
        if cat == "desktop":
            return "desktop" in k or "desktop" in loc
        if cat in ("files", "file", "documents", "downloads", "stuff"):
            return "file" in k or "folder" in k
        if cat in ("folders", "folder", "pastas"):
            return "folder" in k
        return True

    filtered = [it for it in catalog if _category_ok(it)]
    q = (query or "").strip()

    if not q:
        _SYS_FOLDER_NOISE = (
            "administrative tools", "system tools", "accessibility",
            "accessories", "maintenance", "startup", "office tools",
        )
        clean_items = [
            it for it in filtered
            if not any(w in _normalize_text(it.get("name", "")) for w in _NOISY_SHORTCUT_WORDS + ("app recovery", "dfrgui", "run"))
            and not any(sf in it.get("location", "").lower() for sf in _SYS_FOLDER_NOISE)
        ]
        kind_order = {
            "desktop_shortcut": 0,
            "chrome_app_shortcut": 1,
            "taskbar_shortcut": 2,
            "start_menu_shortcut": 3,
            "installed_app": 4,
            "store_app": 5,
            "desktop_folder": 6,
            "desktop_file": 7,
            "user_folder": 8,
            "user_file": 9,
        }
        clean_items.sort(key=lambda x: (kind_order.get(x.get("kind", ""), 99), x.get("name", "").lower()))
        deduped = []
        seen_names = set()
        for it in clean_items:
            key = (_normalize_text(it.get("name", "")), "shortcut" if "shortcut" in it.get("kind", "") else it.get("kind", ""))
            if key in seen_names:
                continue
            seen_names.add(key)
            deduped.append(it)
            if len(deduped) >= limit:
                break
        return deduped

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for it in filtered:
        s = _score_pc_item(it, q, prefer_kind=prefer_kind)
        if s > 0:
            scored.append((s, {**it, "score": s}))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    results: List[Dict[str, Any]] = []
    seen_keys = set()
    for _, it in scored:
        norm_name = _normalize_text(it.get("name", ""))
        group = "app_or_shortcut" if ("shortcut" in it.get("kind", "") or "app" in it.get("kind", "")) else it.get("kind", "")
        if (norm_name, group) in seen_keys:
            continue
        seen_keys.add((norm_name, group))
        results.append(it)
        if len(results) >= limit:
            break
    return results


def find_pc_item(
    query: str,
    category: str = "all",
    min_score: float = 70.0,
    prefer_kind: str = "",
) -> Optional[Dict[str, Any]]:
    """Find the single best matching shortcut, app, Store app, folder, or file on the PC."""
    hits = search_pc_items(
        query=query,
        category=category,
        limit=5,
        include_store_apps=True,
        prefer_kind=prefer_kind,
    )
    if hits and hits[0].get("score", 0) >= min_score:
        return hits[0]
    return None


def launch_pc_item(item: Dict[str, Any]) -> str:
    """Launch a discovered PC shortcut, installed app, Store/UWP app, folder, or file."""
    path = item.get("path", "")
    name = item.get("name", path)
    kind = item.get("kind", "item")
    loc = item.get("location", "")
    if not path:
        return f"No launch path for '{name}'."

    label = f"{loc}" if loc else kind.replace("_", " ")

    # 1. Windows Store / UWP shell:AppsFolder URI
    if path.lower().startswith("shell:appsfolder\\"):
        try:
            subprocess.Popen(
                ["explorer.exe", path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW,
            )
            return f"Opened {name} ({label})."
        except Exception as e:
            return f"Couldn't launch Store app '{name}': {e}"

    # 2. Local file/shortcut/folder via os.startfile (with working directory set for .exe)
    try:
        if os.path.isfile(path) and path.lower().endswith(".exe"):
            subprocess.Popen(
                [path],
                cwd=str(Path(path).parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.startfile(path)
        return f"Opened {name} ({label})."
    except Exception:
        try:
            subprocess.Popen(
                ["explorer.exe", path] if not os.path.isfile(path) else [path],
                cwd=str(Path(path).parent) if os.path.isfile(path) else None,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW,
            )
            return f"Opened {name}."
        except Exception as e:
            return f"Couldn't launch '{name}': {e}"


def scan_pc(query: str = "", category: str = "all", launch_best: bool = False) -> Dict[str, Any]:
    """Scan the PC for apps, shortcuts (.lnk/.url, Chrome Apps, Desktop, Start Menu), Store apps, folders, and files.
    Optionally launch the best match immediately."""
    q = (query or "").strip()
    cat = (category or "all").lower().strip()
    matches = search_pc_items(
        query=q,
        category=cat,
        limit=60 if not q else 12,
        force_refresh=True,
        include_store_apps=True,
    )

    launched_msg = ""
    if launch_best and matches:
        launched_msg = launch_pc_item(matches[0])

    compact_matches = [
        {
            "name": m.get("name"),
            "kind": m.get("kind"),
            "location": m.get("location"),
            "path": m.get("path"),
        }
        for m in matches
    ]

    if q:
        if matches:
            top_names = ", ".join(f"{m['name']} [{m['location']}]" for m in compact_matches[:6])
            summary = f"Found {len(matches)} match(es) for '{q}': {top_names}."
            if launched_msg:
                summary = f"{launched_msg} ({summary})"
        else:
            summary = f"No installed apps, shortcuts, or files matching '{q}' found on this PC."
    else:
        desk_shortcuts = [m["name"] for m in compact_matches if m["kind"] == "desktop_shortcut"]
        chrome_apps = [m["name"] for m in compact_matches if m["kind"] in ("chrome_app_shortcut", "taskbar_shortcut")]
        start_apps = [m["name"] for m in compact_matches if m["kind"] in ("start_menu_shortcut", "installed_app", "store_app")][:18]
        files_folders = [m["name"] for m in compact_matches if "folder" in m["kind"] or "file" in m["kind"]][:10]
        parts = []
        if desk_shortcuts:
            parts.append(f"Desktop shortcuts: {', '.join(desk_shortcuts)}")
        if chrome_apps:
            parts.append(f"Browser/Taskbar shortcuts: {', '.join(chrome_apps)}")
        if start_apps:
            parts.append(f"Installed/Start apps: {', '.join(start_apps)}")
        if files_folders:
            parts.append(f"Desktop/User files & folders: {', '.join(files_folders)}")
        summary = " | ".join(parts) if parts else f"Scanned PC and found {len(compact_matches)} items."

    return {
        "success": True,
        "query": q,
        "category": cat,
        "count": len(compact_matches),
        "launched": launched_msg or None,
        "matches": compact_matches[:25],
        "result": summary,
    }


def youtube_control(action: str = "open", query: str = "") -> str:
    """Open the user's installed YouTube shortcut/app (or search inside it) instead of defaulting to a browser tab."""
    q = (query or "").strip()
    yt_shortcut = find_pc_item("youtube", category="shortcuts", min_score=75.0, prefer_kind="shortcut")

    if not q:
        if yt_shortcut:
            res = launch_pc_item(yt_shortcut)
            focus_window("YouTube", timeout=3.5)
            return res
        return open_target("youtube")

    encoded = urllib.parse.quote(q)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    if yt_shortcut:
        app_id = yt_shortcut.get("app_id", "")
        target_exe = yt_shortcut.get("target_exe", "")
        profile_dir = yt_shortcut.get("profile_dir") or "Default"
        if app_id and target_exe and os.path.isfile(target_exe):
            try:
                subprocess.Popen([
                    target_exe,
                    f"--profile-directory={profile_dir}",
                    f"--app-id={app_id}",
                    f"--app-launch-url-for-shortcuts-menu-item={search_url}",
                ])
                focus_window("YouTube", timeout=4.0)
                return f"Opened installed YouTube app shortcut and searched for '{q}'."
            except Exception:
                pass
        launch_pc_item(yt_shortcut)
        if focus_window("YouTube", timeout=4.0) and pyautogui:
            time.sleep(1.0)
            pyautogui.press("/")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            paste_text(q, press_enter=True)
            return f"Opened YouTube shortcut and searched for '{q}'."

    webbrowser.open(search_url)
    return f"Opened YouTube search for '{q}'."


def _clean_open_query(target: str) -> Tuple[str, str, bool]:
    """Return (cleaned_key, prefer_kind, force_browser) from a natural open target string."""
    t = (target or "").strip().strip('"').rstrip(".!?")
    low = t.lower()
    force_browser = any(low.endswith(s) for s in (" in browser", " on browser", " website", " site", " no navegador"))
    for s in (" in browser", " on browser", " website", " site", " no navegador"):
        if low.endswith(s):
            t = t[:-len(s)].strip()
            low = t.lower()

    prefer_kind = ""
    if any(w in low for w in ("shortcut", "atalho")):
        prefer_kind = "shortcut"
    elif any(w in low for w in ("folder", "directory", "pasta")):
        prefer_kind = "folder"
    elif any(w in low for w in ("file", "document", "doc", "arquivo", "documento")):
        prefer_kind = "file"
    elif any(w in low for w in ("app", "application", "program", "game", "aplicativo", "jogo")):
        prefer_kind = "app"

    key = low
    for prefix in ("the ", "my ", "up ", "o ", "a ", "meu ", "minha "):
        if key.startswith(prefix):
            key = key[len(prefix):].strip()
    for suffix in (
        " shortcut", " atalho", " app", " application", " program", " game",
        " folder", " pasta", " file", " document", " for me", " please", " por favor",
    ):
        if key.endswith(suffix):
            key = key[:-len(suffix)].strip()
    return key or low, prefer_kind, force_browser


def open_target(target: str) -> str:
    """Smart launcher for PC shortcuts (.lnk/.url), installed apps, Chrome Apps, Store apps, folders, files, or web URLs."""
    if not target or not target.strip():
        return "Open what, bro?"
    raw_clean = target.strip().strip('"').rstrip(".!?")
    key, prefer_kind, force_browser = _clean_open_query(raw_clean)

    # Direct file or directory path passed explicitly
    expanded_raw = os.path.expandvars(os.path.expanduser(raw_clean))
    if os.path.exists(expanded_raw):
        try:
            os.startfile(expanded_raw)
            return f"Opened {raw_clean}."
        except Exception as e:
            return f"Couldn't open '{raw_clean}': {e}"

    # Explicit Web URL (e.g. https://... or domain.com)
    if os.path.splitext(raw_clean)[1].lower() not in (".exe", ".lnk", ".url", ".bat", ".cmd", ".docx", ".pdf", ".pptx", ".xlsx", ".txt", ".rtf", ".msc", ".cpl"):
        if raw_clean.startswith(("http://", "https://")) or any(
            key.endswith(ext) for ext in (".com", ".org", ".net", ".io", ".dev", ".ai", ".co", ".app", ".tv", ".gg")
        ):
            url = raw_clean if raw_clean.startswith(("http://", "https://")) else f"https://{key}"
            webbrowser.open(url)
            return f"Opened {raw_clean} in browser."

    if force_browser and key in WEB_FALLBACKS:
        webbrowser.open(WEB_FALLBACKS[key])
        return f"Opened {key} in browser."

    # 1. Core user folders & built-in system utilities / settings pages (when not explicitly asking for a shortcut)
    _CORE_SYSTEM_KEYS = {
        "downloads", "documents", "desktop", "pictures", "photos", "music", "videos",
        "calc", "calculator", "notepad", "paint", "explorer", "file explorer", "files", "this pc", "my computer",
        "settings", "wifi settings", "bluetooth", "bluetooth settings", "sound settings", "audio settings",
        "display settings", "windows update", "apps settings", "installed apps", "storage settings", "battery settings",
        "power settings", "night light", "default apps", "task manager", "control panel", "device manager",
        "disk management", "services", "registry", "regedit", "system info", "system information", "directx", "dxdiag",
        "character map", "charmap", "on screen keyboard", "osk", "magnifier", "disk cleanup", "resource monitor",
        "event viewer", "cmd", "command prompt", "powershell", "terminal", "recycle bin", "snipping tool", "snip",
        "voice recorder", "sound recorder",
    }
    if key in _CORE_SYSTEM_KEYS and prefer_kind != "shortcut" and key in APP_ALIASES:
        sys_target = APP_ALIASES[key]
        try:
            if sys_target.startswith("shell:"):
                subprocess.Popen(["explorer.exe", sys_target], creationflags=_NO_WINDOW)
            else:
                os.startfile(sys_target)
            return f"Opened {key}."
        except Exception:
            pass

    # 2. Scan PC for installed shortcuts (.lnk/.url on Desktop, Chrome Apps, Start Menu, Taskbar),
    #    installed programs, Store/UWP apps, and user files/folders FIRST!
    pc_match = find_pc_item(key, category="all", min_score=74.0, prefer_kind=prefer_kind)
    if pc_match:
        return launch_pc_item(pc_match)

    # 3. Check remaining APP_ALIASES (e.g. word, excel, powerpoint, chrome, edge, vscode, spotify, whatsapp, steam)
    if key in APP_ALIASES:
        alias_target = APP_ALIASES[key]
        if os.path.isfile(alias_target):
            try:
                subprocess.Popen([alias_target], cwd=str(Path(alias_target).parent))
                return f"Opened {key}."
            except Exception as e:
                return f"Couldn't launch '{key}': {e}"
        try:
            if alias_target.startswith("shell:"):
                subprocess.Popen(["explorer.exe", alias_target], creationflags=_NO_WINDOW)
            else:
                os.startfile(alias_target)
            return f"Opened {key}."
        except Exception:
            pass

    # 4. Try slightly broader fuzzy match on PC items before falling back to browser
    fuzzy_match = find_pc_item(key, category="all", min_score=64.0, prefer_kind=prefer_kind)
    if fuzzy_match:
        return launch_pc_item(fuzzy_match)

    # 5. Web Fallbacks (ONLY when no shortcut or app is installed on the PC)
    if key in WEB_FALLBACKS:
        webbrowser.open(WEB_FALLBACKS[key])
        return f"Opened {key} in browser (no local shortcut found)."

    # 6. Native Windows start / shell fallback
    try:
        os.startfile(raw_clean)
        return f"Opened {raw_clean}."
    except Exception:
        pass

    return f"Couldn't find an app, shortcut, or file matching '{raw_clean}' on this PC, bro."


# ---------------------------------------------------------------------------
# Expanded PC Commands: App Closing, Window Control, Media, Power, System
# ---------------------------------------------------------------------------

_user32 = ctypes.windll.user32 if os.name == "nt" else None
SW_MAXIMIZE = 3
SW_RESTORE = 9


def list_open_windows() -> List[Tuple[int, str]]:
    """Return a list of (hwnd, title) for all visible top-level desktop windows."""
    if os.name != "nt" or not _user32:
        return []
    results: List[Tuple[int, str]] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _):
        if not _user32.IsWindowVisible(hwnd):
            return True
        length = _user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title and "acehud" not in title.lower():
            results.append((hwnd, title))
        return True

    _user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return results


_PROCESS_NAME_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "opera": "opera.exe",
    "opera gx": "opera.exe",
    "brave": "brave.exe",
    "firefox": "firefox.exe",
    "word": "WINWORD.EXE",
    "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "spotify": "Spotify.exe",
    "whatsapp": "WhatsApp.exe",
    "discord": "Discord.exe",
    "telegram": "Telegram.exe",
    "steam": "steam.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "vlc": "vlc.exe",
    "task manager": "Taskmgr.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "binance": "Binance.exe",
    "claude": "claude.exe",
    "teams": "ms-teams.exe",
    "lively": "Lively.exe",
    "lively wallpaper": "Lively.exe",
}


def close_app(target: str) -> str:
    """Close an open window or terminate a running application by name."""
    t = (target or "").strip().strip('"').rstrip(".!?")
    if not t:
        return "Close what app, bro?"
    low = t.lower()
    for prefix in ("the ", "my ", "app ", "application ", "window "):
        if low.startswith(prefix):
            low = low[len(prefix):].strip()

    if low in ("active", "current", "this", "this window", "active window", "current window"):
        if pyautogui:
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
        return "Unable to close active window."

    # 1. Try gracefully closing matching open windows via WM_CLOSE
    WM_CLOSE = 0x0010
    closed_titles = []
    for hwnd, title in list_open_windows():
        if low in title.lower():
            try:
                _user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                closed_titles.append(title)
            except Exception:
                pass

    # 2. Also terminate matching process if mapped or found in catalog
    exe_name = _PROCESS_NAME_MAP.get(low)
    if not exe_name:
        match = find_pc_item(low, category="apps", min_score=78.0)
        if match:
            p_str = match.get("target_exe") or match.get("path") or ""
            if p_str.lower().endswith(".exe"):
                exe_name = Path(p_str).name

    if exe_name:
        try:
            subprocess.run(
                ["taskkill", "/IM", exe_name, "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
                creationflags=_NO_WINDOW,
            )
            return f"Closed {t}."
        except Exception:
            pass

    if closed_titles:
        return f"Closed {closed_titles[0]}."

    # 3. Fallback PowerShell Stop-Process by partial name
    try:
        safe = re.sub(r"[^a-zA-Z0-9 _-]", "", low)
        if safe:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 f"Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{safe}*' -or $_.ProcessName -like '*{safe}*' }} | Stop-Process -Force -ErrorAction SilentlyContinue"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
                creationflags=_NO_WINDOW,
            )
            return f"Closed {t}."
    except Exception:
        pass

    return f"Couldn't find a running window or process for '{t}'."


def window_control(action: str, target: str = "") -> str:
    """Manage desktop windows: minimize, maximize, restore, close, show_desktop, minimize_all, snap_left, snap_right, switch, focus, new_tab, close_tab, reopen_tab, refresh, zoom_in, zoom_out, fullscreen."""
    act = (action or "").lower().strip().replace(" ", "_")
    tgt = (target or "").strip()

    if tgt:
        focus_window(tgt, timeout=1.5)

    hwnd = _user32.GetForegroundWindow()

    if act in ("show_desktop", "desktop", "minimize_all", "hide_all"):
        if pyautogui:
            pyautogui.hotkey("win", "d")
            return "Toggled desktop view."
    elif act in ("minimize", "min"):
        if hwnd:
            _user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return f"Minimized {tgt or 'active window'}."
    elif act in ("maximize", "max", "full"):
        if hwnd:
            _user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return f"Maximized {tgt or 'active window'}."
    elif act in ("restore", "unmaximize"):
        if hwnd:
            _user32.ShowWindow(hwnd, SW_RESTORE)
            return f"Restored {tgt or 'active window'}."
    elif act in ("close", "close_window", "quit"):
        if tgt:
            return close_app(tgt)
        if pyautogui:
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
    elif act in ("snap_left", "left", "dock_left"):
        if pyautogui:
            pyautogui.hotkey("win", "left")
            return "Snapped window left."
    elif act in ("snap_right", "right", "dock_right"):
        if pyautogui:
            pyautogui.hotkey("win", "right")
            return "Snapped window right."
    elif act in ("switch", "switch_window", "alt_tab", "next_window"):
        if pyautogui:
            pyautogui.hotkey("alt", "tab")
            return "Switched window."
    elif act in ("task_view", "expose"):
        if pyautogui:
            pyautogui.hotkey("win", "tab")
            return "Opened Task View."
    elif act in ("new_tab",):
        if pyautogui:
            pyautogui.hotkey("ctrl", "t")
            return "Opened new tab."
    elif act in ("close_tab",):
        if pyautogui:
            pyautogui.hotkey("ctrl", "w")
            return "Closed current tab."
    elif act in ("reopen_tab", "restore_tab"):
        if pyautogui:
            pyautogui.hotkey("ctrl", "shift", "t")
            return "Reopened last closed tab."
    elif act in ("next_tab",):
        if pyautogui:
            pyautogui.hotkey("ctrl", "tab")
            return "Switched to next tab."
    elif act in ("prev_tab", "previous_tab"):
        if pyautogui:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return "Switched to previous tab."
    elif act in ("refresh", "reload"):
        if pyautogui:
            pyautogui.press("f5")
            return "Refreshed page."
    elif act in ("fullscreen", "full_screen"):
        if pyautogui:
            pyautogui.press("f11")
            return "Toggled fullscreen."
    elif act in ("zoom_in",):
        if pyautogui:
            pyautogui.hotkey("ctrl", "+")
            return "Zoomed in."
    elif act in ("zoom_out",):
        if pyautogui:
            pyautogui.hotkey("ctrl", "-")
            return "Zoomed out."
    elif act in ("focus", "bring_to_front") and tgt:
        if focus_window(tgt, timeout=2.0):
            return f"Focused {tgt}."
        return open_target(tgt)

    return f"Executed window action '{action}'."


def list_running_apps() -> str:
    """List currently open windows or running user applications on the desktop."""
    wins = list_open_windows()
    ignore = {"program manager", "settings", "microsoft text input application", "windows input experience", "ace"}
    titles = []
    for _, title in wins:
        t_clean = title.strip()
        if t_clean and t_clean.lower() not in ignore and len(t_clean) > 1:
            if t_clean not in titles:
                titles.append(t_clean)
    if titles:
        return f"Open windows ({len(titles)}): " + " | ".join(titles[:12])

    # Fallback: check running user app processes via psutil
    try:
        import psutil
        known_exes = {v.lower(): k.title() for k, v in _PROCESS_NAME_MAP.items()}
        running = []
        for proc in psutil.process_iter(["name"]):
            pname = (proc.info.get("name") or "").lower()
            if pname in known_exes and known_exes[pname] not in running:
                running.append(known_exes[pname])
        if running:
            return f"Running apps ({len(running)}): " + ", ".join(running[:15])
    except Exception:
        pass
    return "No active desktop windows open right now."


def browser_search(query: str, engine: str = "google") -> str:
    """Open a search in Google, YouTube, Bing, DuckDuckGo, GitHub, Amazon, Reddit, or Wikipedia."""
    q = (query or "").strip()
    if not q:
        return "Search for what, bro?"
    eng = (engine or "google").lower().strip()
    if eng in ("youtube", "yt"):
        return youtube_control(action="search", query=q)
    if eng == "spotify":
        return spotify_control(action="play", query=q)

    encoded = urllib.parse.quote(q)
    urls = {
        "google": f"https://www.google.com/search?q={encoded}",
        "bing": f"https://www.bing.com/search?q={encoded}",
        "duckduckgo": f"https://duckduckgo.com/?q={encoded}",
        "github": f"https://github.com/search?q={encoded}",
        "reddit": f"https://www.reddit.com/search/?q={encoded}",
        "amazon": f"https://www.amazon.com/s?k={encoded}",
        "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={encoded}",
    }
    url = urls.get(eng, urls["google"])
    webbrowser.open(url)
    return f"Searched {eng.capitalize()} for '{q}'."


def set_volume(action: str, steps: int = 5) -> str:
    """Adjust system volume: up, down, mute, unmute, max, or a specific percentage (0-100)."""
    if not pyautogui:
        return "Audio controls unavailable."
    act = (action or "").lower().strip().replace("%", "")

    # Check if user passed a specific number like "50" or "set to 80"
    num_m = re.search(r"\b(\d{1,3})\b", act)
    if num_m and act not in ("up", "down"):
        level = max(0, min(100, int(num_m.group(1))))
        # Reset to 0 then step up (each volumeup key is 2% on Windows)
        for _ in range(50):
            pyautogui.press("volumedown")
        for _ in range(round(level / 2)):
            pyautogui.press("volumeup")
        return f"Set volume to ~{level}%."

    if act in ("mute", "unmute", "toggle mute"):
        pyautogui.press("volumemute")
        return "Toggled mute."
    elif act in ("max", "full", "100"):
        for _ in range(50):
            pyautogui.press("volumeup")
        return "Turned volume to 100%."
    elif act in ("min", "zero", "0"):
        for _ in range(50):
            pyautogui.press("volumedown")
        return "Turned volume down to 0%."
    elif "down" in act or "lower" in act or "quieter" in act:
        for _ in range(steps):
            pyautogui.press("volumedown")
        return f"Turned volume down."
    elif "up" in act or "higher" in act or "louder" in act:
        for _ in range(steps):
            pyautogui.press("volumeup")
        return f"Turned volume up."
    return "Unknown volume action."


def set_brightness(level_or_action: str) -> str:
    """Adjust laptop screen brightness (0-100, or 'up' / 'down' / 'max' / 'min')."""
    raw = str(level_or_action or "").lower().strip().replace("%", "")
    target_val: Optional[int] = None
    num_m = re.search(r"\b(\d{1,3})\b", raw)
    if num_m:
        target_val = max(0, min(100, int(num_m.group(1))))
    elif raw in ("max", "full", "high"):
        target_val = 100
    elif raw in ("min", "low", "dim"):
        target_val = 20
    elif raw in ("half", "medium", "normal"):
        target_val = 50

    try:
        if target_val is None:
            # Read current brightness and adjust +/- 20
            delta = 20 if "up" in raw or "bright" in raw or "higher" in raw else -20
            ps_cmd = (
                f"$cur = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness; "
                f"$new = [Math]::Max(0, [Math]::Min(100, $cur + ({delta}))); "
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new); "
                f"Write-Output $new"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdin=subprocess.DEVNULL, text=True, timeout=4, creationflags=_NO_WINDOW
            ).strip()
            return f"Set screen brightness to {out}%."
        else:
            ps_cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target_val})"
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=4, creationflags=_NO_WINDOW,
            )
            return f"Set screen brightness to {target_val}%."
    except Exception:
        return "Couldn't adjust screen brightness on this display."


def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    try:
        # SHEmptyRecycleBinW flags: SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4) = 7
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        return "Emptied the Recycle Bin."
    except Exception as e:
        return f"Couldn't empty Recycle Bin: {e}"


def system_power(action: str) -> str:
    """Perform system power actions: lock, sleep, shutdown, restart, cancel_shutdown."""
    act = (action or "").lower().strip()
    if act in ("lock", "lock pc", "lock screen"):
        return lock_workstation()
    if act in ("sleep", "suspend", "hibernate"):
        subprocess.Popen(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            creationflags=_NO_WINDOW,
        )
        return "Putting PC to sleep."
    if act in ("shutdown", "shut down", "power off", "turn off"):
        subprocess.run(["shutdown", "/s", "/t", "10"], creationflags=_NO_WINDOW)
        return "Shutting down PC in 10 seconds (say 'cancel shutdown' to abort)."
    if act in ("restart", "reboot"):
        subprocess.run(["shutdown", "/r", "/t", "10"], creationflags=_NO_WINDOW)
        return "Restarting PC in 10 seconds (say 'cancel shutdown' to abort)."
    if act in ("cancel", "cancel_shutdown", "abort", "abort shutdown"):
        subprocess.run(["shutdown", "/a"], creationflags=_NO_WINDOW)
        return "Cancelled scheduled shutdown/restart."
    return f"Unknown power action '{action}'."


def get_network_info() -> str:
    """Return local IP address and connected Wi-Fi network name."""
    ip_addr = "unknown"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_addr = s.getsockname()[0]
    except Exception:
        pass
    wifi_ssid = ""
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            stdin=subprocess.DEVNULL, text=True, timeout=3, creationflags=_NO_WINDOW
        )
        m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, flags=re.MULTILINE)
        if m:
            wifi_ssid = m.group(1).strip()
    except Exception:
        pass
    if wifi_ssid:
        return f"Wi-Fi: {wifi_ssid} | Local IP: {ip_addr}."
    return f"Local IP: {ip_addr}."


def get_clipboard() -> str:
    """Read current text from the Windows clipboard."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard"],
            stdin=subprocess.DEVNULL, text=True, timeout=3, creationflags=_NO_WINDOW
        ).strip()
        if not out:
            return "Clipboard is currently empty."
        return f"Clipboard: {out[:300]}"
    except Exception as e:
        return f"Couldn't read clipboard: {e}"


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
    """Retrieve live CPU, RAM, Disk, and Battery percentages."""
    metrics: Dict[str, Any] = {
        "cpu": "?",
        "ram_used_gb": 0,
        "ram_total_gb": 0,
        "ram_percent": 0,
        "disk_free_gb": 0,
        "disk_total_gb": 0,
        "disk_percent": 0,
        "battery": None,
        "charging": None,
    }
    try:
        usage = shutil.disk_usage("C:\\")
        metrics["disk_free_gb"] = round(usage.free / (1024**3), 1)
        metrics["disk_total_gb"] = round(usage.total / (1024**3), 1)
        metrics["disk_percent"] = round((usage.used / usage.total) * 100)
    except Exception:
        pass

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
            metrics["charging"] = bool(bat.power_plugged)
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

