@echo off
REM ===================================================================
REM  Publish StickyNotes v1.1.0: commit the Pro + Gumroad code to
REM  GitHub AND publish it as the free v1.1.0 release (installer + exe).
REM  Double-click to run. Progress -> publish.log
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0publish.log"
echo Publish v1.1.0 started > "%LOG%"
echo. >> "%LOG%"

if exist "_git_lock_trash" rmdir /s /q "_git_lock_trash"
if exist ".git\index.lock" del /f /q ".git\index.lock"

if not exist "installer\StickyNotes_Setup.exe" (
    echo installer missing -- run build_installer.bat first. >> "%LOG%"
    echo PUBLISH_RESULT=NO_INSTALLER >> "%LOG%"
    exit /b 1
)
if not exist "dist\StickyNotes.exe" (
    echo dist exe missing -- run build.bat first. >> "%LOG%"
    echo PUBLISH_RESULT=NO_EXE >> "%LOG%"
    exit /b 1
)

git config user.name "Honcho92" >> "%LOG%" 2>&1
git config user.email "157877105+Honcho92@users.noreply.github.com" >> "%LOG%" 2>&1

echo [1/4] Committing... >> "%LOG%"
git add -A >> "%LOG%" 2>&1
git commit -m "Add Pro tier (licensing, unlimited notes, URL/file/time pins) + Gumroad store integration (v1.1.0)" >> "%LOG%" 2>&1

echo [2/4] Pushing branch... >> "%LOG%"
git push origin fix/windows-hardening >> "%LOG%" 2>&1

echo [3/4] Updating master... >> "%LOG%"
git push origin fix/windows-hardening:master >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo PUBLISH_RESULT=PUSH_FAILED >> "%LOG%"
    exit /b 1
)

echo [4/4] Creating GitHub release v1.1.0 (installer + exe)... >> "%LOG%"
gh release create v1.1.0 "installer\StickyNotes_Setup.exe" "dist\StickyNotes.exe" --title "StickyNotes 1.1.0" --notes-file "release_notes_v1.1.0.md" --target master >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo PUBLISH_RESULT=RELEASE_FAILED >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo PUBLISH_RESULT=SUCCESS >> "%LOG%"
gh release view v1.1.0 --json url --jq ".url" >> "%LOG%" 2>&1
exit /b 0
