"""
Ace Speech Engine - Complete Voice System
- Text-to-Speech (TTS): Direct SAPI.SpVoice async engine on Windows (never hangs Qt/COM),
  with pyttsx3 fallback.
- Speech-to-Text (STT): Real-time microphone listening with wake word detection,
  supporting OpenAI Whisper, Google Speech API, and local recognizers.
"""
import os
import sys
import time
import queue
import threading
import subprocess
import re
from typing import Optional, Callable

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

# Words Google often hears instead of "Ace"
WAKE_PATTERN = re.compile(
    r"^(?:.*?\b)?(?:hey|yo|ok|okay|hi|ei)?[\s,]*\b(ace|ase|aice|eis|ace's|aces)\b[\s,.!?]*",
    re.IGNORECASE,
)
FOLLOW_UP_WINDOW_SEC = 8.0   # after a wake word / reply, keep listening without the wake word
ECHO_GUARD_SEC = 0.8         # ignore audio right after Ace stops talking


class SpeechEngine:
    def __init__(self, tts_engine: str = "sapi5"):
        self.tts_engine = tts_engine
        self._speech_queue = queue.Queue()
        self._is_speaking = False
        self._is_busy = False
        self._last_spoke_at = 0.0
        self._follow_up_until = 0.0
        self._is_listening = False
        self._stop_listening_fn = None
        self._recognizer = None
        self._microphone = None
        self._interrupt = threading.Event()
        self._stt_ready = False  # mic is opened lazily (CLI one-shots don't need it)

        # Background speech worker
        self._tts_worker = threading.Thread(target=self._speech_worker, daemon=True)
        self._tts_worker.start()

    def set_busy(self, busy: bool) -> None:
        self._is_busy = busy

    def _language(self) -> str:
        try:
            from . import ace_config
            return ace_config.get_setting("speechLanguage") or "en-US"
        except Exception:
            return "en-US"

    def _init_stt(self):
        if self._stt_ready:
            return
        self._stt_ready = True
        if sr:
            try:
                self._recognizer = sr.Recognizer()
                self._recognizer.energy_threshold = 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.8
                self._recognizer.non_speaking_duration = 0.4
                self._microphone = sr.Microphone()
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"[AceSpeech] STT init error: {e}")
                self._microphone = None

    def _start_ps_tts(self):
        """Start a persistent hidden PowerShell .NET SpeechSynthesizer process (allowed by App Control, isolated from Qt)."""
        ps_script = (
            "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 1; $s.Volume = 100; "
            "foreach ($v in $s.GetInstalledVoices()) { "
            "  if ($v.VoiceInfo.Name -match 'David') { $s.SelectVoice($v.VoiceInfo.Name); break } "
            "} "
            "while (($line = [Console]::In.ReadLine()) -ne $null) { "
            "  if ($line.Trim().Length -gt 0) { try { $s.Speak($line) } catch {} } "
            "  [Console]::Out.WriteLine('__DONE__'); [Console]::Out.Flush() "
            "}"
        )
        return subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _speech_worker(self):
        ps_proc = None
        if os.name == "nt":
            try:
                ps_proc = self._start_ps_tts()
            except Exception as e:
                print(f"[AceSpeech] PowerShell TTS init error: {e}")
                ps_proc = None

        while True:
            text = self._speech_queue.get()
            try:
                if not text:
                    continue
                self._interrupt.clear()
                self._is_speaking = True

                if os.name == "nt":
                    if ps_proc is None or ps_proc.poll() is not None:
                        ps_proc = self._start_ps_tts()
                    ps_proc.stdin.write(text.replace("\r", " ").replace("\n", " ") + "\n")
                    ps_proc.stdin.flush()
                    # Wait for __DONE__ on stdout while checking for interrupt/timeout
                    done_evt = threading.Event()
                    def _wait_line(p=ps_proc, evt=done_evt):
                        try:
                            p.stdout.readline()
                        except Exception:
                            pass
                        evt.set()
                    threading.Thread(target=_wait_line, daemon=True).start()
                    deadline = time.monotonic() + 20.0
                    while not done_evt.wait(timeout=0.1):
                        if self._interrupt.is_set() or time.monotonic() >= deadline:
                            try:
                                ps_proc.kill()
                            except Exception:
                                pass
                            ps_proc = None
                            break
                elif pyttsx3:
                    tts = pyttsx3.init()
                    tts.say(text)
                    tts.runAndWait()
            except Exception as e:
                print(f"[AceSpeech] Playback error: {e}")
            finally:
                self._is_speaking = False
                self._last_spoke_at = time.monotonic()
                self._speech_queue.task_done()

    def speak(self, text: str, interrupt: bool = False) -> None:
        if not text or not text.strip():
            return
        clean = re.sub(r"[\*_#`>]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()

        if interrupt:
            self._interrupt.set()
            with self._speech_queue.mutex:
                self._speech_queue.queue.clear()

        self._speech_queue.put(clean)

    def wait_until_done(self, timeout: float = 20.0) -> None:
        """Block until everything queued has been spoken."""
        end = time.monotonic() + timeout
        # Brief yield so _speech_worker can pick up the newly queued item
        time.sleep(0.05)
        while (self._is_speaking or not self._speech_queue.empty()) and time.monotonic() < end:
            time.sleep(0.08)

    def is_speaking(self) -> bool:
        return self._is_speaking

    def open_follow_up(self, seconds: float = FOLLOW_UP_WINDOW_SEC) -> None:
        """Allow the next phrase to be accepted without saying the wake word."""
        self._follow_up_until = time.monotonic() + seconds

    def _recognize(self, audio) -> Optional[str]:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                return self._recognizer.recognize_whisper_api(audio, api_key=openai_key)
            except Exception:
                pass
        try:
            return self._recognizer.recognize_google(audio, language=self._language())
        except Exception:
            return None

    def listen_once(self, timeout: int = 5, phrase_limit: int = 10) -> Optional[str]:
        """Listen to the microphone once and return the transcribed text."""
        self._init_stt()
        if not self._recognizer or not self._microphone:
            return None

        try:
            with self._microphone as source:
                print("[AceSpeech] Listening...")
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return self._recognize(audio)
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"[AceSpeech] Recognition error: {e}")
            return None

    def start_wake_word_listener(self, on_wake_callback: Callable[[str], None], wake_words=None):
        """Starts continuous background listening for the wake word ("Ace", "Hey Ace", ...).
        After a wake word or a reply, follow-ups are accepted without it for a few seconds."""
        self._init_stt()
        if not self._recognizer or not self._microphone:
            print("[AceSpeech] No microphone / speech_recognition - voice disabled.")
            return
        if self._stop_listening_fn:
            return  # already listening

        def audio_callback(recognizer, audio):
            # Ignore audio while Ace is thinking, speaking, or right after speaking
            if self._is_busy or self._is_speaking or (time.monotonic() - self._last_spoke_at < ECHO_GUARD_SEC):
                return
            text = self._recognize(audio)
            if not text:
                return
            text = text.strip()
            if self._is_busy or self._is_speaking:
                return
            print(f"[AceVoice Heard]: {text}")

            m = WAKE_PATTERN.match(text)
            if m:
                command = text[m.end():].strip()
                if not command:
                    # Only bare wake word ("Hey Ace") opens follow-up immediately;
                    # actual commands open follow-up after Ace finishes answering.
                    self.open_follow_up()
                on_wake_callback(command)
            elif time.monotonic() < self._follow_up_until:
                self._follow_up_until = 0.0
                on_wake_callback(text)

        self._stop_listening_fn = self._recognizer.listen_in_background(
            self._microphone, audio_callback, phrase_time_limit=8
        )
        self._is_listening = True

    def stop_listener(self):
        if self._stop_listening_fn:
            try:
                self._stop_listening_fn(wait_for_stop=False)
            except Exception:
                pass
            self._stop_listening_fn = None
        self._is_listening = False


# Singleton
_speech_instance = None


def get_speech() -> SpeechEngine:
    global _speech_instance
    if _speech_instance is None:
        _speech_instance = SpeechEngine()
    return _speech_instance


def speak(text: str, interrupt: bool = False):
    get_speech().speak(text, interrupt=interrupt)


def wait_until_done(timeout: float = 20.0):
    get_speech().wait_until_done(timeout)


def listen(timeout: int = 5) -> Optional[str]:
    return get_speech().listen_once(timeout=timeout)
