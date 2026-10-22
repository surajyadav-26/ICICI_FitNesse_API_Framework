@echo off
setlocal

rem ======================================================================
rem ICICI NIRIKSHAN AUTOMATION FRAMEWORK - 1-CLICK ENVIRONMENT SETUP
rem   1. creates .venv (this folder's own Python packages) when it is missing
rem   2. installs requirements.txt into it, retrying on a slow network
rem   3. creates .env from .env.example when it is missing
rem   4. downloads Playwright's Chromium (an installed Chrome or Edge also works without it)
rem Run it once after cloning; then double-click start_server.bat.
rem ======================================================================

cd /d "%~dp0"
title NIRIKSHAN AUTOMATION ENVIRONMENT SETUP
echo ======================================================================
echo ICICI NIRIKSHAN AUTOMATION FRAMEWORK - 1-CLICK ENVIRONMENT SETUP
echo ======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo [ERROR] Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
echo [SUCCESS] Python detected.

rem -- 1. the virtual environment --
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating the virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create .venv. Delete the .venv folder and run this again.
        pause
        exit /b 1
    )
)
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
echo [SUCCESS] Using %VENV_PY%
echo.

rem -- 2. the packages (a slow network can time out, so it retries) --
echo [INFO] Installing required libraries from requirements.txt (this can take a few minutes)...
set TRIES=0
:install
set /a TRIES+=1
"%VENV_PY%" -m pip install -r requirements.txt --quiet --default-timeout 90 --retries 10
if errorlevel 1 (
    if %TRIES% lss 3 (
        echo [WARNING] The download did not finish - trying again ^(%TRIES% of 3^)...
        goto install
    )
    echo [ERROR] Failed to install the libraries. Check the internet / proxy and run this file again.
    pause
    exit /b 1
)
echo [SUCCESS] All python dependencies installed successfully.
echo.

rem -- 3. the settings file --
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [INFO] Created .env from .env.example - open it and set your application URLs and credentials.
) else (
    echo [INFO] .env already exists - left as it is.
)
echo.

rem -- 4. the browser --
echo [INFO] Downloading Playwright Chromium...
"%VENV_PY%" -m playwright install chromium
if errorlevel 1 (
    echo [WARNING] Chromium was not downloaded. Tests still run when Google Chrome or Microsoft Edge is installed
    echo [WARNING] ^(pick it in the browser drop-down^). For Firefox run: python -m playwright install firefox
) else (
    echo [SUCCESS] Playwright Chromium installed.
)
echo.

echo ======================================================================
echo [SUCCESS] SETUP COMPLETED
echo ======================================================================
echo [INFO] Next: edit .env, then double-click start_server.bat to launch the servers.
echo.
pause
