@echo off
REM ===================================================================
REM  Publish StickyNotes v1.0.0 as a GitHub Release (double-click to run).
REM  Updates master to the shipped code and attaches the installer + exe
REM  as downloads. Uses gh (already signed in on this PC).
REM  Writes progress to release.log.
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0release.log"
echo Release started > "%LOG%"
echo. >> "%LOG%"

if exist "_git_lock_trash" rmdir /s /q "_git_lock_trash"
if exist ".git\index.lock" del /f /q ".git\index.lock"

if not exist "installer\StickyNotes_Setup.exe" (
    echo installer\StickyNotes_Setup.exe missing -- run build_installer.bat first. >> "%LOG%"
    echo RELEASE_RESULT=NO_INSTALLER >> "%LOG%"
    exit /b 1
)
if not exist "dist\StickyNotes.exe" (
    echo dist\StickyNotes.exe missing -- run build.bat first. >> "%LOG%"
    echo RELEASE_RESULT=NO_EXE >> "%LOG%"
    exit /b 1
)

echo [1/2] Updating master to the shipped code... >> "%LOG%"
git push origin fix/windows-hardening:master >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo RELEASE_RESULT=PUSH_MASTER_FAILED >> "%LOG%"
    exit /b 1
)

echo [2/2] Creating GitHub release v1.0.0 with installer + exe... >> "%LOG%"
gh release create v1.0.0 "installer\StickyNotes_Setup.exe" "dist\StickyNotes.exe" --title "StickyNotes 1.0.0" --notes-file "release_notes_v1.0.0.md" --target master >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo RELEASE_RESULT=RELEASE_FAILED >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo RELEASE_RESULT=SUCCESS >> "%LOG%"
gh release view v1.0.0 --json url --jq ".url" >> "%LOG%" 2>&1
exit /b 0
