@echo off
REM ===================================================================
REM  Save the StickyNotes polish to GitHub (double-click to run).
REM  Writes progress to push.log so it can be monitored.
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0push.log"

echo Git publish started > "%LOG%"
echo. >> "%LOG%"

REM Clean up stray lock files / trash left by earlier tooling
if exist "_git_lock_trash" rmdir /s /q "_git_lock_trash"
if exist ".git\index.lock" del /f /q ".git\index.lock"
if exist ".git\HEAD.lock" del /f /q ".git\HEAD.lock"

REM Commit with the GitHub no-reply email so your real address stays private
git config user.name "Honcho92" >> "%LOG%" 2>&1
git config user.email "157877105+Honcho92@users.noreply.github.com" >> "%LOG%" 2>&1

echo [1/3] Staging changes... >> "%LOG%"
git add -A >> "%LOG%" 2>&1

echo [2/3] Committing... >> "%LOG%"
git commit -m "Polish for distribution: per-user data dir, single-instance, no-tray fallback, PyInstaller packaging" >> "%LOG%" 2>&1

echo [3/3] Pushing to GitHub... >> "%LOG%"
git push >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo. >> "%LOG%"
    echo PUSH_RESULT=FAILED >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo PUSH_RESULT=SUCCESS >> "%LOG%"
exit /b 0
