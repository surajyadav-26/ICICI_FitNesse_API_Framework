@echo off
setlocal enabledelayedexpansion

rem ═════════════════════════════════════════════════════════════════════
rem ICICI NIRIKSHAN AUTOMATION FRAMEWORK - 1-CLICK ENVIRONMENT SETUP
rem ═════════════════════════════════════════════════════════════════════

title NIRIKSHAN AUTOMATION ENVIRONMENT SETUP
echo =================================════════════════════════════════════
echo ICICI NIRIKSHAN AUTOMATION FRAMEWORK - 1-CLICK ENVIRONMENT SETUP
echo =================================════════════════════════════════════
echo.

rem ── Check for Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo [ERROR] Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [SUCCESS] Python detected.
echo.

rem ── Create Virtual Environment (.venv) ──
if exist ".venv" (
    echo [INFO] Virtual environment (.venv) already exists. Skipping creation...
) else (
    echo [INFO] Creating Python Virtual Environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment!
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment (.venv) created successfully.
)
echo.

rem ── Upgrade Pip and Install Dependencies ──
echo [INFO] Installing required libraries from requirements.txt...
.venv\Scripts\python -m pip install --upgrade pip --quiet
.venv\Scripts\python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies from requirements.txt!
    pause
    exit /b 1
)
echo [SUCCESS] All python dependencies installed successfully.
echo.

rem ── Install Playwright Browsers ──
echo [INFO] Installing Playwright browser binaries (Chromium, Firefox, WebKit)...
.venv\Scripts\playwright install
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browser binaries!
    pause
    exit /b 1
)
echo [SUCCESS] Playwright browser binaries installed and registered successfully.
echo.

echo =================================════════════════════════════════════
echo [SUCCESS] NIRIKSHAN AUTOMATION SETUP COMPLETED FLAWLESSLY!
echo =================================════════════════════════════════════
echo [INFO] You can now double-click start_server.bat to launch your servers!
echo.
pause
