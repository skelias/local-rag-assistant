@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: check prerequisites
if not exist backend\venv (
    echo [ERROR] Please run setup.bat first.
    pause
    exit /b 1
)

:: rebuild frontend if dist missing
if not exist frontend\dist (
    echo [INFO] Building frontend...
    cd frontend
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        pause
        exit /b 1
    )
    cd ..
)

:: open browser
echo [INFO] Starting RAG AI on http://127.0.0.1:8000
start "" http://127.0.0.1:8000

:: start server
cd backend
venv\Scripts\python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000
