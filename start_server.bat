@echo off
title FitNesse ICICI Pru AML Test Suite Server (SECURE)
echo =====================================================================
echo  Starting FitNesse + Python API Framework Server (Branded: ICICI Pru)
echo  [SECURITY] Authentication is ENABLED. Login required to access portal.
echo =====================================================================

:: Set PYTHONPATH to the directory of this batch file
set "PYTHONPATH=%~dp0"
echo [INFO] PYTHONPATH set to: %PYTHONPATH%

:: Activate Python Virtual Environment
if not exist "%~dp0.venv\Scripts\activate.bat" goto no_venv
echo [INFO] Activating Python virtual environment (.venv)...
call "%~dp0.venv\Scripts\activate.bat"
goto clean_ports

:no_venv
echo [WARNING] Python virtual environment (.venv) not found.
echo [WARNING] Running using system-wide Python.
goto clean_ports

:clean_ports
:: Automatically terminate any old Java/FitNesse/Mock processes currently holding port 8080 or 8089
echo [INFO] Scanning and clearing ports 8080 and 8089 to prevent server conflicts...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8089') do taskkill /f /pid %%a >nul 2>&1
goto check_java

:check_java
:: Force Java 8 for FitNesse compatibility
echo [INFO] Searching for Java 8 installation...

:: Try to find Java 8
set "JAVA_HOME_BACKUP=%JAVA_HOME%"
set "JAVA8_FOUND="

if exist "C:\Program Files\Java\jdk1.8.0_*" (
    for /d %%i in ("C:\Program Files\Java\jdk1.8.0_*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

if exist "C:\Program Files (x86)\Java\jdk1.8.0_*" (
    for /d %%i in ("C:\Program Files (x86)\Java\jdk1.8.0_*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

if exist "C:\Program Files\Java\jre1.8.0_*" (
    for /d %%i in ("C:\Program Files\Java\jre1.8.0_*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

if exist "C:\Program Files (x86)\Java\jre1.8.0_*" (
    for /d %%i in ("C:\Program Files (x86)\Java\jre1.8.0_*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

if exist "C:\Program Files (x86)\Java\jre-1.8*" (
    for /d %%i in ("C:\Program Files (x86)\Java\jre-1.8*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

if exist "C:\Program Files\Java\jre-1.8*" (
    for /d %%i in ("C:\Program Files\Java\jre-1.8*") do (
        set "JAVA_HOME=%%i"
        set "JAVA8_FOUND=1"
        goto found_java8
    )
)

:: If Java 8 not found, just use whatever Java is available
if not defined JAVA8_FOUND (
    echo [WARNING] Java 8 not found in standard locations. Using system Java...
    java -version >nul 2>&1
    if errorlevel 1 goto no_java
    goto launch_fitnesse
)

:found_java8
set "PATH=%JAVA_HOME%\bin;%PATH%"
echo [SUCCESS] Using Java 8 from: %JAVA_HOME%
"%JAVA_HOME%\bin\java" -version
goto launch_fitnesse

:no_java
echo [ERROR] Java is not installed or not in system PATH.
echo [ERROR] FitNesse requires Java 8 or higher to run.
pause
exit /b 1

:launch_fitnesse
:: Launch FitNesse Server using Java with Classpath to load the plugins and ICICI Theme!
echo [INFO] Launching FitNesse on http://localhost:8080/UserTests
echo [INFO] Loading custom ICICI Pru Banking Theme templates and properties...
echo [INFO] Using JSON-backed application role access...
echo [INFO] Starting Real-Time Folder-Sync Self-Healing Watcher in background...

:: Silently launch our real-time folder-sync self-healing watcher! 🟢
start /b .venv\Scripts\python "%~dp0core\fitnesse_watcher.py"
:: Start the file-backed UI user store on localhost:8090
start "Nirikshan User Store" /b .venv\Scripts\python "%~dp0core\user_store_server.py"

echo [INFO] Press Ctrl+C in this terminal to stop the server.
echo ---------------------------------------------------------------------

:: Use explicit Java path if JAVA_HOME is set, otherwise use system java
if defined JAVA_HOME (
    "%JAVA_HOME%\bin\java" -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p 8080
) else (
    java -cp "%~dp0.;%~dp0fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p 8080
)
