@echo off
REM ===================================================================
REM  Build StickyNotes.exe  (double-click this file to run it)
REM  Writes progress to build.log so it can be monitored.
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0build.log"

echo StickyNotes build started > "%LOG%"
echo. >> "%LOG%"

echo [1/2] Installing dependencies (needs internet)... >> "%LOG%"
python -m pip install --upgrade pip >> "%LOG%" 2>&1
python -m pip install -r requirements.txt pyinstaller >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo. >> "%LOG%"
    echo BUILD_RESULT=DEPS_FAILED >> "%LOG%"
    echo Dependency install failed. Is Python 3.9+ installed and on your PATH? >> "%LOG%"
    exit /b 1
)

echo [2/2] Building one-file executable... >> "%LOG%"
python -m PyInstaller --noconfirm --clean StickyNotes.spec >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo. >> "%LOG%"
    echo BUILD_RESULT=BUILD_FAILED >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo BUILD_RESULT=SUCCESS >> "%LOG%"
echo Your app is at: dist\StickyNotes.exe >> "%LOG%"
exit /b 0
