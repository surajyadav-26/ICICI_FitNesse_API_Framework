@echo off
setlocal

rem ═════════════════════════════════════════════════════════════════════
rem ICICI NIRIKSHAN AUTOMATION SERVER LAUNCHER (start_server.bat)
rem ═════════════════════════════════════════════════════════════════════

cd /d "%~dp0"
title NIRIKSHAN AUTOMATION SERVER

echo [INFO] Commencing system checks...
echo [INFO] Current Working Directory: %CD%

rem ── Set PYTHONPATH to the absolute workspace root to guarantee clean imports ──
set PYTHONPATH=%~dp0

rem ── Check for .env file presence ──
if not exist ".env" (
    echo [WARNING] .env file not found.
    echo [INFO] Copying template .env.example to create a new .env configuration...
    copy ".env.example" ".env" >nul
)

rem ── Check for Python and install project requirements (no virtual environment) ──
python --version >nul 2>&1
if errorlevel 1 goto no_python
python -c "import waferslim, requests, dotenv, playwright" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required libraries from requirements.txt...
    python -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto no_python
)

rem ── Check for Java runtime ──
java -version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Java is not installed or not in PATH!
    echo [ERROR] FitNesse requires Java to run.
    goto no_java
)

rem ── Ports of THIS copy come from .env (FITNESSE_PORT, STORE_PORT, MOCK_SERVER_PORT) through core/config.py ──
for /f "delims=" %%p in ('python -W ignore -c "from core.config import Config; print(Config.FITNESSE_PORT)" 2^>nul') do set FITNESSE_PORT=%%p
for /f "delims=" %%p in ('python -W ignore -c "from core.config import Config; print(Config.STORE_PORT)" 2^>nul') do set STORE_PORT=%%p
for /f "delims=" %%p in ('python -W ignore -c "from core.config import Config; print(Config.MOCK_SERVER_PORT)" 2^>nul') do set MOCK_SERVER_PORT=%%p
if not defined FITNESSE_PORT set FITNESSE_PORT=8080
if not defined STORE_PORT set STORE_PORT=8090
if not defined MOCK_SERVER_PORT set MOCK_SERVER_PORT=8089

rem ── Free only THIS copy's ports. Other Java / Python programs (and other copies of the framework) are left alone ──
echo [INFO] Freeing ports %FITNESSE_PORT%, %STORE_PORT% and %MOCK_SERVER_PORT%...
for %%q in (%FITNESSE_PORT% %STORE_PORT% %MOCK_SERVER_PORT%) do (
    for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /R /C:":%%q .*LISTENING"') do taskkill /f /pid %%a >nul 2>&1
)

echo [INFO] Cleansing old results to start session fresh...
del /q /s "%~dp0FitNesseRoot\files\testResults\allure-results\*" >nul 2>&1
del /q /s "%~dp0FitNesseRoot\files\testResults\allure-report\*" >nul 2>&1
del /q "%~dp0FitNesseRoot\files\report_history.json" >nul 2>&1
del /q "%~dp0FitNesseRoot\files\report.html" >nul 2>&1
for /d %%p in ("%~dp0FitNesseRoot\files\testResults\*") do (
    if /i not "%%~nxp"=="allure-results" if /i not "%%~nxp"=="allure-report" if /i not "%%~nxp"=="ui-automation" (
        rd /s /q "%%p" >nul 2>&1
    )
)

rem ── Start the user store / report server in the background ──
echo [INFO] Starting JSON-backed Local User Store Server on port %STORE_PORT%...
start "Nirikshan User Store" /b python "%~dp0core\user_store_server.py"
if errorlevel 1 (
    echo [WARNING] Failed to start User Store Server. UI account edits may be disabled.
)

rem ── Start FitNesse Standalone Server ──
echo [INFO] Starting FitNesse Acceptor Engine on port %FITNESSE_PORT%...
echo [INFO] Launching FitNesse on http://localhost:%FITNESSE_PORT%/

rem Inject Java 25 bypasses (-Dprevent.system.exit=false), timezone silencer (-Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false), sequential thread pool (-Dfitnesse.runner.parallel=1), and modular bypasses (--add-opens) for a pristine console run on ALL Java versions
if defined JAVA_HOME (
    "%JAVA_HOME%\bin\java" -Dfitnesse.runner.parallel=1 -Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false -Dprevent.system.exit=false -Dfitnesse.security.manager.enabled=false --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p %FITNESSE_PORT%
) else (
    java -Dfitnesse.runner.parallel=1 -Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false -Dprevent.system.exit=false -Dfitnesse.security.manager.enabled=false --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p %FITNESSE_PORT%
)

goto end

:no_python
echo [FATAL] Python setup failed. Please make sure Python is installed.
pause
exit /b 1

:no_java
echo [FATAL] Java is required. Please install Java 8, 11, 17, or 21 and try again.
pause
exit /b 1

:end
echo [INFO] Nirikshan Automation session ended.
pause
