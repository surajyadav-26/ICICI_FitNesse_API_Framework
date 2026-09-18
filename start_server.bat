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

rem ── Check if Python Virtual Environment is active ──
if not exist ".venv" (
    echo [ERROR] Python Virtual Environment .venv is missing!
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto no_python
)

rem ── Activate Python Virtual Environment in the current session ──
echo [INFO] Activating Python Virtual Environment...
call .venv\Scripts\activate.bat

rem ── Check for Java runtime ──
java -version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Java is not installed or not in PATH!
    echo [ERROR] FitNesse requires Java to run.
    goto no_java
)

rem ── Force-kill any lingering zombie Python, FitNesse, or SLiM processes to free up ports and prevent duplicate SlimService runs ──
echo [INFO] Flushing and cleaning all zombie background processes...
taskkill /f /im java.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr 8085') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr 8080') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr 8090') do taskkill /f /pid %%a >nul 2>&1

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

rem ── Start Nirikshan User Store Server on port 8090 in the background ──
echo [INFO] Starting JSON-backed Local User Store Server on port 8090...
start "Nirikshan User Store" /b .venv\Scripts\python "%~dp0core\user_store_server.py"
if errorlevel 1 (
    echo [WARNING] Failed to start User Store Server. UI account edits may be disabled.
)

rem ── Start FitNesse Standalone Server on port 8080 ──
echo [INFO] Starting FitNesse Acceptor Engine on port 8080...
echo [INFO] Launching FitNesse on http://localhost:8080/

rem Inject Java 25 bypasses (-Dprevent.system.exit=false), timezone silencer (-Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false), sequential thread pool (-Dfitnesse.runner.parallel=1), and modular bypasses (--add-opens) for a pristine console run on ALL Java versions
if defined JAVA_HOME (
    "%JAVA_HOME%\bin\java" -Dfitnesse.runner.parallel=1 -Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false -Dprevent.system.exit=false -Dfitnesse.security.manager.enabled=false --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p 8080
) else (
    java -Dfitnesse.runner.parallel=1 -Duser.timezone=Asia/Kolkata -Dsun.timezone.ids.oldmapping=false -Dprevent.system.exit=false -Dfitnesse.security.manager.enabled=false --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p 8080
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
