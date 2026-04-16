@echo off
REM Install dependencies for StickyNotes
echo Installing StickyNotes dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Installation failed. Make sure Python 3.9+ is installed and on your PATH.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.
echo Done! You can now double-click run.bat to start StickyNotes.
pause
