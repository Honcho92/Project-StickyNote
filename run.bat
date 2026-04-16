@echo off
REM Launch StickyNotes (no console window)
cd /d "%~dp0"
start "" pythonw app.py
