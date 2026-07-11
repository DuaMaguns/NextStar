@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHON_CMD=python
set VENV_DIR=venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe

echo ===============================================
echo          StarPath Navigator - College Planner
echo ===============================================
echo.

if not exist "%VENV_DIR%" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment Python not found: %VENV_PYTHON%
    pause
    exit /b 1
)

echo [INFO] Installing dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [INFO] Python Path: %VENV_PYTHON%
echo [INFO] Starting service...
echo [INFO] Visit: http://localhost:5000 after startup
echo [INFO] Press Ctrl+C to stop the service
echo.

"%VENV_PYTHON%" app.py

pause
