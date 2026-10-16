"""
Ace Python CLI Runner
Usage:
  python ace.py "What time is it?"
  python ace.py "open spotify"
  python ace.py (interactive mode)
  python ace.py start | pill | gui   -> launch floating pill HUD (detached)
  python ace.py stop                 -> close any running HUD
  python ace.py restart              -> stop + start the HUD
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

UI_SCRIPT = PROJECT_ROOT / "core" / "ace_ui.py"
PID_FILE = PROJECT_ROOT / "ipc" / "ace_ui.pid"

# --- HUD process control -------------------------------------------------

def _find_ui_pids():
    """Return PIDs of every running process whose command line contains ace_ui.py
    (catches HUDs started by `ace start` AND by Launch-Ace.bat)."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%ace_ui.py%'\" | "
        "Where-Object { $_.ProcessId -ne $PID -and $_.Name -like 'python*' } | "
        "ForEach-Object { $_.ProcessId }"
    )
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return []
    return [int(x) for x in out.split() if x.strip().isdigit()]


def start_hud():
    running = _find_ui_pids()
    if running:
        print(f"[ACE] Pill HUD already running (PID {', '.join(map(str, running))}).")
        return 0

    exe_dir = Path(sys.executable).parent
    pythonw = exe_dir / "pythonw.exe"
    interpreter = str(pythonw if pythonw.exists() else sys.executable)

    flags = 0
    if os.name == "nt":
        flags = (subprocess.DETACHED_PROCESS
                 | subprocess.CREATE_NEW_PROCESS_GROUP
                 | subprocess.CREATE_NO_WINDOW)

    proc = subprocess.Popen(
        [interpreter, str(UI_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags, close_fds=True,
    )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))
    print(f"[ACE] Pill HUD launched (PID {proc.pid}).")
    return 0


def stop_hud():
    # Note: a venv's pythonw.exe is a launcher that spawns the real interpreter,
    # so one HUD normally appears as two PIDs (launcher + child).
    pids = _find_ui_pids()
    if not pids:
        print("[ACE] Pill HUD is not running.")
    else:
        for pid in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True)
        print(f"[ACE] Pill HUD closed (PID {', '.join(map(str, pids))}).")
    PID_FILE.unlink(missing_ok=True)
    return 0


HUD_COMMANDS = {
    "start": start_hud,
    "pill": start_hud,
    "gui": start_hud,
    "stop": stop_hud,
    "restart": lambda: (stop_hud(), start_hud())[1],
}

def main():
    args = sys.argv[1:]

    # HUD control commands (handled before loading the brain/speech modules)
    if len(args) == 1 and args[0].lower() in HUD_COMMANDS:
        return HUD_COMMANDS[args[0].lower()]()

    from core.ace_brain import ask_ace
    from core.ace_speech import speak, listen, get_speech, wait_until_done
    from core import ace_config

    # Direct single-command execution
    if args and not args[0].startswith("--"):
        query = " ".join(args)
        res = ask_ace(query)
        reply = res.get("reply", "")
        print(f"\n[Ace]: {reply}\n")
        if os.environ.get("ACE_NO_SPEAK") != "1":
            speak(reply)
            wait_until_done(timeout=45)
        return

    # Continuous Voice Mode
    if "--voice" in args:
        print("\n==========================================")
        print("  ACE VOICE LISTENER ACTIVE")
        print("  Say 'Ace' or 'Hey Ace' followed by your command.")
        print("  Press Ctrl+C to stop.")
        print("==========================================\n")
        
        def on_wake(command_text):
            print(f"\n[You]: {command_text}")
            res = ask_ace(command_text)
            reply = res.get("reply", "")
            print(f"[Ace]: {reply}\n")
            speak(reply)

        sp = get_speech()
        sp.start_wake_word_listener(on_wake)
        try:
            while True:
                import time
                time.sleep(0.5)
        except KeyboardInterrupt:
            sp.stop_listener()
            print("\nVoice listener stopped.")
            return

    # Interactive Terminal Mode
    user_name = ace_config.get_user_name()
    print(f"\n==========================================")
    print(f"  ACE AI COPILOT (Python Engine)")
    print(f"  Ready for {user_name}. (Type 'voice' to speak, 'exit' to quit)")
    print(f"==========================================\n")

    while True:
        try:
            inp = input(f"{user_name}> ").strip()
            if not inp:
                continue
            if inp.lower() in ["exit", "quit", "q"]:
                speak("Later bro!")
                print("Later bro!")
                break
            if inp.lower() in ["voice", "speak", "listen", "mic"]:
                print("Listening now... speak into your mic:")
                heard = listen(timeout=6)
                if heard:
                    print(f"[Heard]: {heard}")
                    inp = heard
                else:
                    print("Didn't catch that, bro.")
                    continue

            res = ask_ace(inp)
            reply = res.get("reply", "")
            print(f"Ace> {reply}\n")
            speak(reply)
        except (KeyboardInterrupt, EOFError):
            print("\nLater bro!")
            break

if __name__ == "__main__":
    main()
