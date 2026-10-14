"""
Ace Speech Engine - Modular Voice System
Supports:
- pyttsx3 (Current offline, zero-latency engine)
- Bark (Extensible architecture ready for Suno/Bark neural speech)
- Whisper (Extensible architecture ready for OpenAI Whisper STT)
"""
import sys
import threading
import queue
import re
from typing import Optional

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class SpeechEngine:
    def __init__(self, voice_engine: str = "pyttsx3"):
        self.engine_name = voice_engine
        self._queue = queue.Queue()
        self._is_speaking = False
        self._tts = None
        self._init_tts()

        # Background worker for non-blocking speech
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _init_tts(self):
        if self.engine_name == "pyttsx3" and pyttsx3:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 175)
                self._tts.setProperty("volume", 1.0)
                # Try to pick a natural male/clean voice like David
                voices = self._tts.getProperty("voices")
                for v in voices:
                    if "david" in v.name.lower():
                        self._tts.setProperty("voice", v.id)
                        break
            except Exception as e:
                print(f"[AceSpeech] pyttsx3 init error: {e}")
                self._tts = None

    def _speech_worker(self):
        while True:
            text = self._queue.get()
            if not text:
                continue
            self._is_speaking = True
            try:
                if self.engine_name == "pyttsx3" and self._tts:
                    self._tts.say(text)
                    self._tts.runAndWait()
                elif self.engine_name == "bark":
                    # Placeholder for Bark neural pipeline
                    pass
            except Exception as e:
                print(f"[AceSpeech] Speech playback error: {e}")
            finally:
                self._is_speaking = False
                self._queue.task_done()

    def speak(self, text: str, interrupt: bool = False) -> None:
        if not text or not text.strip():
            return
        # Clean markdown symbols (*, `, #, etc.)
        clean = re.sub(r"[\*_#`>]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()

        if interrupt and self.engine_name == "pyttsx3" and self._tts:
            try:
                self._tts.stop()
            except Exception:
                pass
            with self._queue.mutex:
                self._queue.queue.clear()

        self._queue.put(clean)

    def is_speaking(self) -> bool:
        return self._is_speaking

# Singleton instance
_global_speech = None

def get_speech_engine() -> SpeechEngine:
    global _global_speech
    if _global_speech is None:
        _global_speech = SpeechEngine()
    return _global_speech

def speak(text: str, interrupt: bool = False) -> None:
    engine = get_speech_engine()
    engine.speak(text, interrupt=interrupt)
