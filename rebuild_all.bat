@echo off
REM ==================================================================
REM  Rebuild StickyNotes end-to-end. Double-click this ONE file.
REM  The window STAYS OPEN at the end so you can read the result.
REM ==================================================================
cd /d "%~dp0"
echo.
echo ==== STEP 1 of 2: Building StickyNotes.exe (this takes 1-2 min) ====
echo.
call build.bat
if %errorlevel% neq 0 (
    echo.
    echo *** BUILD FAILED -- see build.log ***
    echo.
    pause
    exit /b 1
)
echo Build step finished.
echo.
echo ==== STEP 2 of 2: Building the installer ====
echo.
call build_installer.bat
if %errorlevel% neq 0 (
    echo.
    echo *** INSTALLER FAILED -- see installer.log ***
    echo.
    pause
    exit /b 1
)
echo.
echo ================================================================
echo  ALL DONE. Both files rebuilt:
echo    dist\StickyNotes.exe
echo    installer\StickyNotes_Setup.exe
echo ================================================================
echo.
echo You can close this window now.
pause
