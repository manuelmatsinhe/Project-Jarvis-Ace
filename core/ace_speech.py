"""
Ace Speech Engine - Complete Voice System
- Text-to-Speech (TTS): Fast, zero-lag local engine with clean speech queueing.
- Speech-to-Text (STT): Real-time microphone listening with wake word detection,
  supporting OpenAI Whisper, Google Speech API, and local recognizers.
- Modular architecture ready for Bark and Whisper model weights.
"""
import os
import sys
import time
import queue
import threading
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

class SpeechEngine:
    def __init__(self, tts_engine: str = "pyttsx3"):
        self.tts_engine = tts_engine
        self._speech_queue = queue.Queue()
        self._is_speaking = False
        self._is_listening = False
        self._stop_listening_fn = None
        self._tts = None
        self._recognizer = None
        self._microphone = None

        self._init_tts()
        self._init_stt()

        # Background speech worker
        self._tts_worker = threading.Thread(target=self._speech_worker, daemon=True)
        self._tts_worker.start()

    def _init_tts(self):
        if pyttsx3:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 180)
                self._tts.setProperty("volume", 1.0)
                voices = self._tts.getProperty("voices")
                for v in voices:
                    if "david" in v.name.lower():
                        self._tts.setProperty("voice", v.id)
                        break
            except Exception as e:
                print(f"[AceSpeech] pyttsx3 init error: {e}")

    def _init_stt(self):
        if sr:
            try:
                self._recognizer = sr.Recognizer()
                self._recognizer.energy_threshold = 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.8
                self._microphone = sr.Microphone()
                # Quick ambient noise calibration
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"[AceSpeech] STT init error: {e}")

    def _speech_worker(self):
        while True:
            text = self._speech_queue.get()
            if not text:
                continue
            self._is_speaking = True
            try:
                if self._tts:
                    self._tts.say(text)
                    self._tts.runAndWait()
            except Exception as e:
                print(f"[AceSpeech] Playback error: {e}")
            finally:
                self._is_speaking = False
                self._speech_queue.task_done()

    def speak(self, text: str, interrupt: bool = False) -> None:
        if not text or not text.strip():
            return
        clean = re.sub(r"[\*_#`>]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()

        if interrupt and self._tts:
            try:
                self._tts.stop()
            except Exception:
                pass
            with self._speech_queue.mutex:
                self._speech_queue.queue.clear()

        self._speech_queue.put(clean)

    def is_speaking(self) -> bool:
        return self._is_speaking

    def listen_once(self, timeout: int = 5, phrase_limit: int = 8) -> Optional[str]:
        """Listen to the microphone once and return the transcribed text."""
        if not self._recognizer or not self._microphone:
            return None

        try:
            with self._microphone as source:
                print("[AceSpeech] Listening...")
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            # Try OpenAI Whisper if OPENAI_API_KEY is present
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                try:
                    return self._recognizer.recognize_whisper_api(audio, api_key=openai_key)
                except Exception:
                    pass

            # Fast online recognizer fallback
            try:
                return self._recognizer.recognize_google(audio)
            except Exception:
                return None

        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"[AceSpeech] Recognition error: {e}")
            return None

    def start_wake_word_listener(self, on_wake_callback: Callable[[str], None], wake_words=("ace", "hey ace", "yo ace")):
        """Starts continuous background listening for wake words."""
        if not self._recognizer or not self._microphone:
            return

        def audio_callback(recognizer, audio):
            if self._is_speaking:
                return  # Don't listen while Ace is talking
            try:
                text = recognizer.recognize_google(audio).lower().strip()
                print(f"[AceVoice Heard]: {text}")
                for w in wake_words:
                    if text.startswith(w) or w in text:
                        # Strip wake word and trigger
                        cleaned = re.sub(rf"^{w}[,\s]*", "", text).strip()
                        on_wake_callback(cleaned or text)
                        break
            except Exception:
                pass

        self._stop_listening_fn = self._recognizer.listen_in_background(
            self._microphone, audio_callback, phrase_time_limit=6
        )
        self._is_listening = True

    def stop_listener(self):
        if self._stop_listening_fn:
            self._stop_listening_fn(wait_for_stop=False)
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

def listen(timeout: int = 5) -> Optional[str]:
    return get_speech().listen_once(timeout=timeout)
