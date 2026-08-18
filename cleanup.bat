@echo off
REM ===================================================================
REM  Remove the throwaway _signtest artifact from the repo and keep it
REM  ignored going forward. Double-click to run. Progress -> cleanup.log
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0cleanup.log"
echo Cleanup started > "%LOG%"

if exist "_git_lock_trash" rmdir /s /q "_git_lock_trash"
if exist ".git\index.lock" del /f /q ".git\index.lock"

REM Add _signtest/ to .gitignore only if it isn't already there
findstr /x /c:"_signtest/" .gitignore >nul 2>&1
if errorlevel 1 >>.gitignore echo _signtest/

git config user.name "Honcho92" >> "%LOG%" 2>&1
git config user.email "157877105+Honcho92@users.noreply.github.com" >> "%LOG%" 2>&1

echo [1/3] Untracking _signtest... >> "%LOG%"
git rm -r --cached _signtest >> "%LOG%" 2>&1

echo [2/3] Committing... >> "%LOG%"
git add -A >> "%LOG%" 2>&1
git commit -m "Stop tracking _signtest test artifact and gitignore it" >> "%LOG%" 2>&1

echo [3/3] Pushing branch + master... >> "%LOG%"
git push origin fix/windows-hardening >> "%LOG%" 2>&1
git push origin fix/windows-hardening:master >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo CLEANUP_RESULT=PUSH_FAILED >> "%LOG%"
    exit /b 1
)

echo CLEANUP_RESULT=SUCCESS >> "%LOG%"
exit /b 0
