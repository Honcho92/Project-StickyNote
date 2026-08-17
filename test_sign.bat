@echo off
REM ===================================================================
REM  Test the code-signing pipeline with a THROWAWAY self-signed cert.
REM  Proves signtool + the signing command work on this machine.
REM  Signs a COPY only -- it never touches the real deliverables.
REM  Writes progress to signtest.log.
REM ===================================================================
cd /d "%~dp0"
set "LOG=%~dp0signtest.log"
echo Sign-pipeline test started > "%LOG%"
echo. >> "%LOG%"

echo [1/4] Creating a throwaway self-signed code-signing certificate... >> "%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $c = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=StickyNotes Test Cert' -CertStoreLocation Cert:\CurrentUser\My; $pw = ConvertTo-SecureString -String 'test123' -Force -AsPlainText; Export-PfxCertificate -Cert $c -FilePath 'test_cert.pfx' -Password $pw | Out-Null; Remove-Item $c.PSPath; 'cert created' } catch { Write-Output $_; exit 1 }" >> "%LOG%" 2>&1
if not exist "test_cert.pfx" (
    echo SIGNTEST_RESULT=CERT_FAILED >> "%LOG%"
    exit /b 1
)

echo [2/4] Locating signtool.exe... >> "%LOG%"
set "SIGNTOOL="
for /f "delims=" %%F in ('where /r "%ProgramFiles(x86)%\Windows Kits\10\bin" signtool.exe 2^>nul') do set "SIGNTOOL=%%F"
if not defined SIGNTOOL for /f "delims=" %%F in ('where signtool.exe 2^>nul') do set "SIGNTOOL=%%F"
if not defined SIGNTOOL (
    echo signtool.exe not found -- the Windows SDK signing tools are not installed. >> "%LOG%"
    echo SIGNTEST_RESULT=NO_SIGNTOOL >> "%LOG%"
    del /q "test_cert.pfx" 2>nul
    exit /b 1
)
echo Using signtool: %SIGNTOOL% >> "%LOG%"

echo [3/4] Signing a throwaway copy of the app... >> "%LOG%"
if not exist "_signtest" mkdir "_signtest"
copy /y "dist\StickyNotes.exe" "_signtest\StickyNotes_signed_test.exe" >> "%LOG%" 2>&1
"%SIGNTOOL%" sign /f "test_cert.pfx" /p "test123" /fd SHA256 "_signtest\StickyNotes_signed_test.exe" >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
    echo SIGNTEST_RESULT=SIGN_FAILED >> "%LOG%"
    del /q "test_cert.pfx" 2>nul
    exit /b 1
)

echo [4/4] Verifying signature is embedded... >> "%LOG%"
"%SIGNTOOL%" verify /pa /v "_signtest\StickyNotes_signed_test.exe" >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo SIGNTEST_RESULT=SUCCESS >> "%LOG%"
echo Note: a self-signed cert reports an untrusted root -- that is EXPECTED. >> "%LOG%"
echo A real purchased cert will verify as trusted with the same sign.bat command. >> "%LOG%"
del /q "test_cert.pfx" 2>nul
exit /b 0
