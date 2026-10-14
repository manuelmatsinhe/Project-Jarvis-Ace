# 🤖 Project Jarvis // ACE (Virtual Twin & PC Co-Pilot)

> **Ace** is an always-on-screen desktop companion inspired by Iron Man's Jarvis and modern dynamic islands. He lives in any of your screen's four corners as an animated vector avatar ("Little Man Ace"), listens to voice commands, types into apps for you, opens files and programs, learns your slang and speech patterns, and can be summoned anywhere via CMD or PowerShell.

---

## 🚀 Quick Start

You can open this entire project folder in your IDE (VS Code / Antigravity IDE):
**Path:** `C:\Users\hp\Documents\Project-Jarvis-Ace`

### 1. Launch Ace (Dynamic Island)
- **From Windows Explorer / IDE:** Double-click [`Launch-Ace.bat`](file:///C:/Users/hp/Documents/Project-Jarvis-Ace/Launch-Ace.bat).
- **From any CMD or PowerShell:**
  ```powershell
  ace start
  ```

### 2. Teach Ace to Be Like You (Persona Calibration)
Run the calibration interview so Ace learns your speech style, slang, typing preference, and autonomy level:
- **From Windows Explorer / IDE:** Double-click [`Calibrate-Ace.bat`](file:///C:/Users/hp/Documents/Project-Jarvis-Ace/Calibrate-Ace.bat).
- **From Terminal:**
  ```powershell
  ace learn
  # or
  ace interview
  ```

---

## 🕹️ Controls & Features

### 🖥️ 1. Dynamic Island HUD
- **4-Corner Snapping:**
  - `[TL]` -> Top Left corner
  - `[TR]` -> Top Right corner *(default)*
  - `[BL]` -> Bottom Left corner
  - `[BR]` -> Bottom Right corner
  - You can also drag Ace freely with your mouse anywhere on screen!
- **Expand / Collapse:** Click the `+` / `x` button on the island pill to toggle the full HUD deck.
- **Animated Little Man Avatar:**
  - **Cyan Visor & Blinking Eyes:** Idle & ready for orders.
  - **Emerald Visor:** Listening to microphone voice commands.
  - **Amber Visor:** Thinking / Profiling your persona.
  - **Purple Visor:** Actively executing (typing, launching apps, moving).

### ⌨️ 2. Terminal Commands (`ace` in CMD or PowerShell)
The `ace` CLI is installed globally across your system:

| Command | Description |
| :--- | :--- |
| `ace start` | Spawns Ace Dynamic Island if not already active |
| `ace stop` | Puts Ace to sleep |
| `ace corner <TL\|TR\|BL\|BR>` | Snaps Ace to any screen corner in real time |
| `ace open <app\|file\|url>` | Opens any program, folder, file, or URL (e.g. `ace open notepad`, `ace open chrome`, `ace open downloads`, `ace open youtube`) |
| `ace type <text>` | Types text directly into whatever app you have open |
| `ace learn` | Launches Ace's persona interview to teach him your speech style |
| `ace status` | Checks PC metrics (RAM usage, CPU, runtime health) |
| `ace speak <message>` | Makes Ace speak out loud through your speakers |

### 🎙️ 3. Voice Commands (Speech Recognition)
Ace has offline Windows speech recognition built-in. When the Mic is toggled ON (`Mic: ON`), you can speak:
- *"Hey Ace"*
- *"Ace open notepad"*
- *"Ace open browser"*
- *"Ace open youtube"*
- *"Ace open downloads"*
- *"Ace open calculator"*
- *"Ace type hello"*
- *"Ace corner top left / top right / bottom left / bottom right"*
- *"Ace status"*
- *"Ace interview"*

---

## 🧬 Project Structure

```text
C:\Users\hp\Documents\Project-Jarvis-Ace\
├── Launch-Ace.bat        # One-click launcher for Ace Dynamic Island
├── Calibrate-Ace.bat     # One-click launcher for Persona Calibration
├── README.md             # Project documentation & guide
├── config/
│   ├── settings.json     # Screen corner, audio preferences, typing delay
│   └── profile.json      # Learned persona (slang, catchphrases, speech style)
├── core/
│   ├── ace_agent.ps1     # WPF Dynamic Island UI, Little Man avatar, event loop
│   ├── ace_actions.ps1   # PC actuation (typing simulation, opening apps/files)
│   ├── ace_speech.ps1    # Offline text-to-speech & voice recognition listener
│   ├── ace_personality.ps1# Persona adaptation & response styling engine
│   └── ace_interview.ps1 # Interactive interview to train Ace on your persona
├── cli/
│   ├── ace.cmd           # CMD command wrapper
│   └── ace.ps1           # PowerShell command wrapper
└── ipc/
    ├── queue.json        # Fast IPC command queue between CLI and Ace GUI
    ├── response.json     # Execution status logs
    └── ace.lock          # Runtime lock containing Ace PID
```

---

## 💡 How Ace Learns You

When you run `ace learn`, Ace stores your personalized profile in [`config/profile.json`](file:///C:/Users/hp/Documents/Project-Jarvis-Ace/config/profile.json):
- **Callsign:** How Ace addresses you (Bro, Boss, Chief, etc.).
- **Speech Style:** Casual Bro, Chill Coder, or Direct & Fast.
- **Slang:** Your favorite catchphrases (`bet`, `say less`, `let's cook`, etc.) which Ace incorporates into his voice and text messages.
- **Autonomy Mode:** Proactive Doer (nudges you, takes initiative) vs Silent Executor (only speaks when summoned).
