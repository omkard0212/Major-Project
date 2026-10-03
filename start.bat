@echo off
echo ============================================
echo   ArthSathi - Starting...
echo ============================================
echo.

:: ── Quick checks before starting ─────────────────────────────

:: Check .env exists
if not exist "backend\config\.env" (
    echo [ERROR] backend\config\.env not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

:: Check processed dataset exists
if not exist "ml-model\schemes_processed.csv" (
    echo [INFO] Processed dataset not found. Running parser...
    cd ml-model
    python parse_schemes.py
    cd ..
    echo [OK] Dataset ready.
)

:: Check PostgreSQL service is running
sc query postgresql-x64-16 | find "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Starting PostgreSQL service...
    net start postgresql-x64-16 >nul 2>&1
)

:: ── Start Backend (Flask) ─────────────────────────────────────
echo Starting Backend...
start "ArthSathi Backend" cmd /k "cd /d %~dp0backend && python app.py"

:: Wait for backend to be ready
timeout /t 3 /nobreak >nul

:: ── Start Frontend (HTTP Server) ─────────────────────────────
echo Starting Frontend...
start "ArthSathi Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 8080"

:: Wait a moment then open browser
timeout /t 2 /nobreak >nul

:: ── Open browser ──────────────────────────────────────────────
echo Opening ArthSathi in browser...
start http://localhost:8080

echo.
echo ============================================
echo   ArthSathi is running!
echo   Frontend : http://localhost:8080
echo   Backend  : http://localhost:5000
echo   
echo   Close this window to keep it running.
echo   Close the Backend and Frontend windows to stop.
echo ============================================
echo.
