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
from core.ace_speech import speak
from core import ace_config

def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        res = ask_ace(query)
        reply = res.get("reply", "")
        print(f"\n[Ace]: {reply}\n")
        return

    user_name = ace_config.get_user_name()
    print(f"\n==========================================")
    print(f"  ACE AI COPILOT (Python Engine)")
    print(f"  Ready for {user_name}. Type 'exit' to quit.")
    print(f"==========================================\n")

    while True:
        try:
            inp = input(f"{user_name}> ").strip()
            if not inp:
                continue
            if inp.lower() in ["exit", "quit", "q"]:
                print("Later bro!")
                break
            res = ask_ace(inp)
            reply = res.get("reply", "")
            print(f"Ace> {reply}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nLater bro!")
            break

if __name__ == "__main__":
    main()
