@echo off
REM ===================================================================
REM  Build StickyNotes.exe  (a single, self-contained Windows program)
REM  Run this from a normal terminal with an internet connection.
REM ===================================================================
cd /d "%~dp0"

echo Installing runtime + build dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if %errorlevel% neq 0 (
    echo.
    echo Dependency install failed. Make sure Python 3.9+ is installed and on your PATH.
    pause
    exit /b 1
)

echo.
echo Building one-file executable (this can take a minute)...
python -m PyInstaller --noconfirm --clean StickyNotes.spec
if %errorlevel% neq 0 (
    echo.
    echo Build failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done!  Your app is here:  dist\StickyNotes.exe
echo  Double-click it to run. No Python needed on the target PC.
echo ============================================================
pause
