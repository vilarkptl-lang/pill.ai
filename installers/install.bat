@echo off
REM pill.ai — one-click installer for Windows
REM Usage: install.bat [--key PILLAI-XXXX-XXXX-XXXX-XXXX]

setlocal EnableDelayedExpansion
set REPO=https://github.com/vilarkptl-lang/pill.ai
set INSTALL_DIR=%USERPROFILE%\.pill.ai\app
set LICENSE_KEY=

REM Parse args
:parse_args
if "%1"=="--key" (
    set LICENSE_KEY=%2
    shift & shift
    goto parse_args
)

echo.
echo   pill.ai — Ultra-cheap multi-agent computer AI
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+ from https://python.org
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo ^[OK^] Python %PY_VER%

REM Create directories
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Create venv
python -m venv "%INSTALL_DIR%\venv"
call "%INSTALL_DIR%\venv\Scripts\activate.bat"
echo ^[OK^] Virtual environment created

REM Clone / update
if exist "%INSTALL_DIR%\src\.git" (
    echo   Updating...
    git -C "%INSTALL_DIR%\src" pull --ff-only
) else (
    git clone --depth=1 %REPO% "%INSTALL_DIR%\src"
)
echo ^[OK^] Source code ready

REM Install
pip install --quiet --upgrade pip
pip install --quiet -e "%INSTALL_DIR%\src[dashboard]"
echo ^[OK^] Dependencies installed

REM Playwright
python -m playwright install chromium 2>nul
echo ^[OK^] Browser installed

REM Activate license
if not "%LICENSE_KEY%"=="" (
    pillai activate %LICENSE_KEY%
)

echo.
echo ====================================================
echo   pill.ai installed! Open a new terminal and run:
echo.
echo   pillai
echo   pillai activate ^<YOUR-KEY^>
echo   pillai status
echo.
echo   Pricing: https://pill.ai/pricing
echo ====================================================
echo.
pause
