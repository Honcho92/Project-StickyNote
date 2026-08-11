@echo off
REM ===================================================================
REM  Build StickyNotes_Setup.exe (a proper Windows installer).
REM  Double-click to run. Writes progress to installer.log.
REM  Needs Inno Setup; if it's missing this will install it via winget
REM  (you may see a one-time Windows "Do you want to allow..." prompt --
REM   click Yes).
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0installer.log"
echo Installer build started > "%LOG%"
echo. >> "%LOG%"

if not exist "dist\StickyNotes.exe" (
    echo dist\StickyNotes.exe not found -- run build.bat first. >> "%LOG%"
    echo INSTALLER_RESULT=NO_EXE >> "%LOG%"
    exit /b 1
)

REM Find the Inno Setup command-line compiler (ISCC.exe)
set "ISCC="
for %%P in (
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
) do if exist %%~P set "ISCC=%%~P"

if not defined ISCC (
    echo Inno Setup not found. Installing it via winget... >> "%LOG%"
    winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
    for %%P in (
        "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
        "%ProgramFiles%\Inno Setup 6\ISCC.exe"
        "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    ) do if exist %%~P set "ISCC=%%~P"
)

if not defined ISCC (
    echo Could not find or install Inno Setup automatically. >> "%LOG%"
    echo Install it once from https://jrsoftware.org/isdl.php then re-run this. >> "%LOG%"
    echo INSTALLER_RESULT=NO_INNO >> "%LOG%"
    exit /b 1
)

echo Using compiler: %ISCC% >> "%LOG%"
echo Building installer... >> "%LOG%"
"%ISCC%" "StickyNotes.iss" >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo INSTALLER_RESULT=BUILD_FAILED >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo INSTALLER_RESULT=SUCCESS >> "%LOG%"
echo Installer is at: installer\StickyNotes_Setup.exe >> "%LOG%"
exit /b 0
