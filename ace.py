"""
Ace Python CLI Runner
Usage:
  python ace.py "What time is it?"
  python ace.py "open spotify"
  python ace.py (interactive mode)
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.ace_brain import ask_ace
from core.ace_speech import speak, listen, get_speech
from core import ace_config

def main():
    args = sys.argv[1:]
    
    # Direct single-command execution
    if args and not args[0].startswith("--"):
        query = " ".join(args)
        res = ask_ace(query)
        reply = res.get("reply", "")
        print(f"\n[Ace]: {reply}\n")
        speak(reply)
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
