"""
Ace Desktop HUD - Floating PySide6 Jarvis-style Assistant Bar
Features:
- Always-Listening hands-free voice by default (wake word: "Ace" / "Hey Ace")
- Direct text input box (press Enter to execute)
- Real-time animated audio equalizer strips (only active while thinking/speaking)
- Live status indicator: Listening, Thinking, Speaking, Muted
- Clean Mute toggle button (only click if you want him NOT to listen)
- Draggable anywhere on the desktop
- Zero-glitch layered window geometry on Windows (no QGraphicsDropShadowEffect clipping)
"""
import os
import re
import sys
import random
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, Signal, QObject
from PySide6.QtGui import QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QFrame, QMenu
)

from core.ace_brain import ask_ace
from core.ace_speech import speak, get_speech

PILL_WIDTH = 520
PILL_HEIGHT = 50


class WorkerSignals(QObject):
    response_ready = Signal(str)
    voice_heard = Signal(str)
    status_changed = Signal(str)


class AudioWaveWidget(QWidget):
    """Sleek real-time equalizer bars. Only animates when active to prevent idle UI lag."""
    IDLE_BARS = [3, 4, 6, 8, 6, 4, 3]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.is_active = False
        self.active_color = QColor("#00E5FF")
        self.bar_heights = list(self.IDLE_BARS)
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._animate_bars)

    def set_active(self, active: bool, color_hex: str = "#00E5FF"):
        self.active_color = QColor(color_hex)
        if active == self.is_active:
            self.update()
            return
        self.is_active = active
        if active:
            self._timer.start()
        else:
            self._timer.stop()
            self.bar_heights = list(self.IDLE_BARS)
        self.update()

    def _animate_bars(self):
        if self.is_active:
            self.bar_heights = [random.randint(4, 20) for _ in range(7)]
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen( QPen(Qt.NoPen))

        color = self.active_color if self.is_active else QColor("#6E6E7A")
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
        self._is_busy = False
        self._shutting_down = False
        self._cmd_seq = 0
        self.speech_engine = get_speech()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_response)

        self._init_window()
        self._init_ui()
        self._sync_window_size()
        self._start_voice_listener()

        # Pre-warm PC catalog in background so first command is <1ms
        def _warm_catalog():
            try:
                from . import ace_actions
                ace_actions.scan_pc_catalog(force_refresh=True, include_store_apps=True)
            except Exception:
                pass

        threading.Thread(target=_warm_catalog, daemon=True).start()

        # Track active app window continuously (every 250ms) so Ace always knows where the user is
        self._active_app_timer = QTimer(self)
        self._active_app_timer.setInterval(250)
        self._active_app_timer.timeout.connect(self._track_foreground_window)
        self._active_app_timer.start()

    def _track_foreground_window(self):
        try:
            from . import ace_actions
            ace_actions.get_active_app_context()
        except Exception:
            pass

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(PILL_WIDTH)

        # Position in top-right corner by default
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(max(20, screen.right() - PILL_WIDTH - 24), screen.top() + 24)

    def _set_pill_border(self, border_color: str = "#282834"):
        self.pill.setStyleSheet(f"""
            QFrame#AcePill {{
                background-color: rgba(18, 18, 22, 245);
                border: 1.5px solid {border_color};
                border-radius: 25px;
            }}
        """)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(6)
        self.main_layout.setAlignment(Qt.AlignTop)

        # Floating Pill Container (locked height so it never stretches or squishes)
        self.pill = QFrame(self)
        self.pill.setObjectName("AcePill")
        self.pill.setFixedHeight(PILL_HEIGHT)
        self._set_pill_border("#282834")

        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(16, 6, 12, 6)
        pill_layout.setSpacing(10)

        # Status badge / Icon
        self.status_icon = QLabel("●", self.pill)
        self.status_icon.setFixedWidth(14)
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setStyleSheet("color: #00E5FF; font-size: 14px; background: transparent; border: none;")
        pill_layout.addWidget(self.status_icon)

        # Equalizer Wave
        self.wave = AudioWaveWidget(self.pill)
        pill_layout.addWidget(self.wave)

        # Text Input Box
        self.input_box = QLineEdit(self.pill)
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
        self.btn_mute = QPushButton("Mic On", self.pill)
        self.btn_mute.setCursor(Qt.PointingHandCursor)
        self.btn_mute.setFixedHeight(26)
        self.btn_mute.setStyleSheet("""
            QPushButton {
                background-color: #1C1C22;
                border: 1px solid #33333F;
                color: #00E5FF;
                border-radius: 13px;
                padding: 0px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #262630;
            }
        """)
        self.btn_mute.clicked.connect(self._toggle_mute)
        pill_layout.addWidget(self.btn_mute)

        # Exit Button
        self.btn_exit = QPushButton("✕", self.pill)
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_exit.setToolTip("Exit Ace (Esc)")
        self.btn_exit.setFixedSize(26, 26)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #1C1C22;
                border: 1px solid #33333F;
                color: #AAAAAA;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A2020;
                border: 1px solid #FF5252;
                color: #FFFFFF;
            }
        """)
        self.btn_exit.clicked.connect(self._exit_app)
        pill_layout.addWidget(self.btn_exit)

        self.main_layout.addWidget(self.pill)

        # Response Toast / Bubble
        self.response_label = QLabel("", self)
        self.response_label.setObjectName("ResponseLabel")
        self.response_label.setFixedWidth(PILL_WIDTH - 16)
        self.response_label.setStyleSheet("""
            QLabel#ResponseLabel {
                background-color: rgba(18, 18, 24, 240);
                color: #EAEAEF;
                border: 1px solid #2E2E3C;
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.response_label.setWordWrap(True)
        self.response_label.hide()
        self.main_layout.addWidget(self.response_label)

    def _sync_window_size(self):
        """Recalculate exact window height so the pill never shifts or clips."""
        self.main_layout.invalidate()
        self.main_layout.activate()
        target_h = max(PILL_HEIGHT + 12, self.main_layout.totalSizeHint().height())
        self.setFixedSize(PILL_WIDTH, target_h)

    # --- Mouse Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # --- Exit Options ---
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._exit_app()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        exit_action = menu.addAction("Exit Ace")
        if menu.exec(event.globalPos()) == exit_action:
            self._exit_app()

    def closeEvent(self, event):
        event.accept()
        if not self._shutting_down:
            self._exit_app()

    @staticmethod
    def _is_exit_command(text: str) -> bool:
        t = re.sub(r"[!.?]+$", "", (text or "").strip().lower())
        return t in (
            "exit", "quit", "q", "exit ace", "quit ace", "close ace",
            "stop ace", "turn off ace", "shut down ace", "kill ace",
        )

    def _exit_app(self):
        if self._shutting_down:
            os._exit(0)
        self._shutting_down = True
        self._is_busy = True
        self._cmd_seq += 1
        try:
            self._active_app_timer.stop()
            self._hide_timer.stop()
            self.wave.set_active(False)
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.speech_engine.shutdown()
        except Exception:
            pass
        try:
            (PROJECT_ROOT / "ipc" / "ace_ui.pid").unlink(missing_ok=True)
        except Exception:
            pass
        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
        os._exit(0)

    # --- Interaction Logic ---
    def _on_text_submitted(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        if self._is_exit_command(text):
            self._exit_app()
            return
        self._process_command(text)

    def _process_command(self, query: str):
        if self._is_busy or self._shutting_down:
            return
        if self._is_exit_command(query):
            self._exit_app()
            return
        self._is_busy = True
        self._cmd_seq += 1
        my_seq = self._cmd_seq
        self.speech_engine.set_busy(True)
        self.signals.status_changed.emit("Thinking...")

        def worker():
            try:
                if not query.strip():
                    reply = "Yo, I'm listening."  # bare wake word -> instant ack
                else:
                    res = ask_ace(query)
                    reply = res.get("reply", "") or "Hmm, I got nothing on that one, bro."
            except Exception as e:
                print(f"[AceHUD] Brain error: {e}")
                reply = "Something glitched on my end, bro. Try that again."

            if self._shutting_down:
                return

            # Release _is_busy right after thinking so typed commands are never ignored while speaking
            self._is_busy = False
            self.signals.response_ready.emit(reply)
            self.signals.status_changed.emit("Speaking...")
            try:
                speak(reply, interrupt=True)
                self.speech_engine.wait_until_done(timeout=18)
                if not self._shutting_down and self._cmd_seq == my_seq:
                    self.speech_engine.open_follow_up()  # answer back without saying "Ace"
            except Exception as e:
                print(f"[AceHUD] Speech error: {e}")
            finally:
                if not self._shutting_down and self._cmd_seq == my_seq:
                    self.speech_engine.set_busy(False)
                    if not self._is_busy:
                        self.signals.status_changed.emit("Listening")

        threading.Thread(target=worker, daemon=True).start()

    def _on_response_ready(self, reply: str):
        if self._shutting_down:
            return
        self.response_label.setText(reply)
        self.response_label.show()
        self._sync_window_size()
        self._hide_timer.start(max(7000, min(16000, 65 * len(reply))))

    def _hide_response(self):
        self.response_label.hide()
        self._sync_window_size()

    def _on_voice_heard(self, text: str):
        if self._is_busy or self._shutting_down:
            return
        if self._is_exit_command(text):
            self._exit_app()
            return
        self.input_box.setText(text)
        self._process_command(text)

    def _on_status_changed(self, status: str):
        if self.is_muted:
            self.status_icon.setStyleSheet("color: #FF5252; font-size: 14px; background: transparent; border: none;")
            self._set_pill_border("#4A2020")
            self.wave.set_active(False)
            return

        if status == "Listening":
            self.status_icon.setStyleSheet("color: #00E5FF; font-size: 14px; background: transparent; border: none;")
            self._set_pill_border("#282834")
            self.wave.set_active(False)
        elif status == "Thinking...":
            self.status_icon.setStyleSheet("color: #FFD600; font-size: 14px; background: transparent; border: none;")
            self._set_pill_border("#7A6400")
            self.wave.set_active(True, "#FFD600")
        elif status == "Speaking...":
            self.status_icon.setStyleSheet("color: #00E676; font-size: 14px; background: transparent; border: none;")
            self._set_pill_border("#1E6B45")
            self.wave.set_active(True, "#00E676")

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
                    border-radius: 13px;
                    padding: 0px 10px;
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
                    border-radius: 13px;
                    padding: 0px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.signals.status_changed.emit("Listening")

    def _start_voice_listener(self):
        if self.is_muted:
            return

        def on_wake(command_text):
            if not self.is_muted and not self._is_busy:
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
