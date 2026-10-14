"""
Ace Desktop HUD - Floating PySide6 Jarvis-style Assistant Bar
Features:
- Always-Listening hands-free voice by default (wake word: "Ace" / "Hey Ace")
- Direct text input box (press Enter to execute)
- Real-time animated audio equalizer strips
- Live status indicator: Listening, Thinking, Speaking, Muted
- Clean Mute toggle button (only click if you want him NOT to listen)
- Draggable anywhere on the desktop
"""
import sys
import math
import random
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, Signal, QObject
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QGraphicsDropShadowEffect, QFrame
)

from core.ace_brain import ask_ace
from core.ace_speech import speak, get_speech
from core import ace_config

class WorkerSignals(QObject):
    response_ready = Signal(str)
    voice_heard = Signal(str)
    status_changed = Signal(str)

class AudioWaveWidget(QWidget):
    """Sleek real-time equalizer bars."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.is_active = False
        self.bar_heights = [4, 6, 12, 18, 10, 6, 4]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_bars)
        self._timer.start(80)

    def set_active(self, active: bool):
        self.is_active = active

    def _animate_bars(self):
        if self.is_active:
            self.bar_heights = [random.randint(4, 20) for _ in range(7)]
        else:
            self.bar_heights = [3, 4, 6, 8, 6, 4, 3]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(Qt.NoPen)
        painter.setPen(pen)

        color = QColor("#00E5FF") if self.is_active else QColor("#888888")
        painter.setBrush(QBrush(color))

        spacing = 6
        start_x = 4
        center_y = self.height() // 2

        for i, h in enumerate(self.bar_heights):
            x = start_x + (i * spacing)
            y = center_y - (h // 2)
            painter.drawRoundedRect(QRectF(x, y, 3, h), 1.5, 1.5)

class AceHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.signals.response_ready.connect(self._on_response_ready)
        self.signals.voice_heard.connect(self._on_voice_heard)
        self.signals.status_changed.connect(self._on_status_changed)

        self.drag_position = QPoint()
        self.is_muted = False
        self.speech_engine = get_speech()

        self._init_window()
        self._init_ui()
        self._start_voice_listener()

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(520, 110)

        # Position in top-right corner by default
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 560, 50)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # Floating Pill Container
        self.pill = QFrame(self)
        self.pill.setObjectName("AcePill")
        self.pill.setStyleSheet("""
            QFrame#AcePill {
                background-color: #121214;
                border: 1px solid #282830;
                border-radius: 24px;
            }
        """)

        # Drop shadow for futuristic floating feel
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.pill.setGraphicsEffect(shadow)

        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(14, 8, 14, 8)
        pill_layout.setSpacing(10)

        # Status badge / Icon
        self.status_icon = QLabel("●", self)
        self.status_icon.setStyleSheet("color: #00E5FF; font-size: 14px;")
        pill_layout.addWidget(self.status_icon)

        # Equalizer Wave
        self.wave = AudioWaveWidget(self)
        pill_layout.addWidget(self.wave)

        # Text Input Box
        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("Talk or type a command... (Enter to run)")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FAFAFA;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                padding: 4px;
            }
            QLineEdit:focus {
                color: #FFFFFF;
            }
        """)
        self.input_box.returnPressed.connect(self._on_text_submitted)
        pill_layout.addWidget(self.input_box, 1)

        # Mute Toggle Button
        self.btn_mute = QPushButton("Mic On", self)
        self.btn_mute.setCursor(Qt.PointingHandCursor)
        self.btn_mute.setStyleSheet("""
            QPushButton {
                background-color: #1C1C22;
                border: 1px solid #33333F;
                color: #00E5FF;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #262630;
            }
        """)
        self.btn_mute.clicked.connect(self._toggle_mute)
        pill_layout.addWidget(self.btn_mute)

        main_layout.addWidget(self.pill)

        # Response Toast / Bubble
        self.response_label = QLabel("", self)
        self.response_label.setObjectName("ResponseLabel")
        self.response_label.setStyleSheet("""
            QLabel#ResponseLabel {
                background-color: rgba(20, 20, 24, 230);
                color: #E2E2E6;
                border: 1px solid #2B2B36;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.response_label.setWordWrap(True)
        self.response_label.hide()
        main_layout.addWidget(self.response_label)

    # --- Mouse Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # --- Interaction Logic ---
    def _on_text_submitted(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self._process_command(text)

    def _process_command(self, query: str):
        self.signals.status_changed.emit("Thinking...")
        self.wave.set_active(True)

        def worker():
            res = ask_ace(query)
            reply = res.get("reply", "")
            self.signals.response_ready.emit(reply)
            self.signals.status_changed.emit("Speaking...")
            speak(reply)
            self.signals.status_changed.emit("Listening")

        threading.Thread(target=worker, daemon=True).start()

    def _on_response_ready(self, reply: str):
        self.response_label.setText(reply)
        self.response_label.show()
        # Auto-hide toast after 8 seconds
        QTimer.singleShot(8000, self.response_label.hide)

    def _on_voice_heard(self, text: str):
        self.input_box.setText(text)
        self._process_command(text)

    def _on_status_changed(self, status: str):
        if self.is_muted:
            self.status_icon.setStyleSheet("color: #FF5252;")
            self.wave.set_active(False)
            return

        if status == "Listening":
            self.status_icon.setStyleSheet("color: #00E5FF;")
            self.wave.set_active(False)
        elif status == "Thinking...":
            self.status_icon.setStyleSheet("color: #FFD600;")
            self.wave.set_active(True)
        elif status == "Speaking...":
            self.status_icon.setStyleSheet("color: #00E676;")
            self.wave.set_active(True)

    def _toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.speech_engine.stop_listener()
            self.btn_mute.setText("Muted")
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background-color: #2A1515;
                    border: 1px solid #5A2020;
                    color: #FF5252;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.signals.status_changed.emit("Muted")
        else:
            self._start_voice_listener()
            self.btn_mute.setText("Mic On")
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background-color: #1C1C22;
                    border: 1px solid #33333F;
                    color: #00E5FF;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.signals.status_changed.emit("Listening")

    def _start_voice_listener(self):
        if self.is_muted:
            return

        def on_wake(command_text):
            if not self.is_muted:
                self.signals.voice_heard.emit(command_text)

        self.speech_engine.start_wake_word_listener(on_wake)
        self.signals.status_changed.emit("Listening")

def launch_hud():
    app = QApplication(sys.argv)
    hud = AceHUD()
    hud.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_hud()
