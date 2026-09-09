@echo off
chcp 65001 >nul
echo ============================================
echo   RAG AI - Environment Setup
echo ============================================
echo.

cd /d "%~dp0"

:: .env
if not exist .env (
    copy .env.example .env >nul
    echo [INFO] Created .env from .env.example
    echo [INFO] Please edit .env and fill in your API keys
    echo.
)

:: backend venv
if not exist backend\venv (
    echo [1/3] Creating Python virtual environment...
    cd backend
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Python 3.12+ is required. Install it first.
        pause
        exit /b 1
    )
    venv\Scripts\pip install -U pip -q
    echo [1/3] Installing Python dependencies...
    venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
    cd ..
) else (
    echo [1/3] Python venv already exists - skipping.
)

:: frontend
if not exist frontend\node_modules (
    echo [2/3] Installing frontend dependencies...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    cd ..
) else (
    echo [2/3] Frontend node_modules already exists - skipping.
)

:: build frontend
if not exist frontend\dist (
    echo [3/3] Building frontend...
    cd frontend
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        pause
        exit /b 1
    )
    cd ..
) else (
    echo [3/3] Frontend dist already built - skipping.
)

echo.
echo ============================================
echo   Setup complete!
echo   Next: edit .env with your API keys,
echo   then run start.bat
echo ============================================
pause
