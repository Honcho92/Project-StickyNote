@echo off
REM ===================================================================
REM  Code-sign StickyNotes so customers don't get the SmartScreen
REM  "unknown publisher" warning.
REM
REM  You need a code-signing certificate first (see SHIPPING.md).
REM  Then put the .pfx file in this folder and run, e.g.:
REM      sign.bat mycert.pfx MyPfxPassword
REM ===================================================================
cd /d "%~dp0"
set "PFX=%~1"
set "PW=%~2"
if "%PFX%"=="" set "PFX=cert.pfx"

if not exist "%PFX%" (
    echo Certificate "%PFX%" not found in this folder.
    echo Put your .pfx there, or pass its path:  sign.bat path\to\cert.pfx password
    pause
    exit /b 1
)

REM Locate signtool.exe (ships with the Windows SDK)
set "SIGNTOOL="
for /f "delims=" %%F in ('where /r "%ProgramFiles(x86)%\Windows Kits\10\bin" signtool.exe 2^>nul') do set "SIGNTOOL=%%F"
if not defined SIGNTOOL for /f "delims=" %%F in ('where signtool.exe 2^>nul') do set "SIGNTOOL=%%F"
if not defined SIGNTOOL (
    echo signtool.exe not found. Install the Windows SDK signing tools first.
    echo https://developer.microsoft.com/windows/downloads/windows-sdk/
    pause
    exit /b 1
)

for %%T in ("dist\StickyNotes.exe" "installer\StickyNotes_Setup.exe") do (
    if exist %%T (
        echo Signing %%T ...
        "%SIGNTOOL%" sign /f "%PFX%" /p "%PW%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 %%T
    )
)

echo.
echo Done. To verify:  "%SIGNTOOL%" verify /pa dist\StickyNotes.exe
pause
