@echo off
REM ===================================================================
REM  Quick test of the new voice-note feature, straight from source
REM  (no packaging). Faster to iterate than a full rebuild.
REM  IMPORTANT: quit any running StickyNotes first (tray icon -> Quit),
REM  or this will just exit (single-instance guard).
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0voice_test.log"
echo Installing dependencies (first run downloads whisper + audio libs)... 
echo Voice test started > "%LOG%"
python -m pip install -r requirements.txt >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo *** Dependency install FAILED -- see voice_test.log ***
    echo.
    pause
    exit /b 1
)
echo.
echo Launching StickyNotes from source...
echo   1. Click the microphone button on a note
echo   2. Speak a sentence, click it again to stop
echo   3. First time downloads the voice model (~140 MB, one time)
echo   4. Your words should appear in the note
echo.
echo (Close the app window when done, then close this window.)
python app.py
pause
