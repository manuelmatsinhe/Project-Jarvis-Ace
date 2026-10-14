@echo off
REM Double-click to launch Ace (no console window stays open)
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0core\ace_agent.ps1"
