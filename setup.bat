@echo off
echo ============================================
echo   ArthSathi - First Time Setup
echo ============================================
echo.

:: ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found.

:: ── Install Python packages ───────────────────────────────────
echo.
echo Installing Python packages...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)
echo [OK] Python packages installed.

:: ── Check PostgreSQL ──────────────────────────────────────────
echo.
echo Checking PostgreSQL...
"C:\Program Files\PostgreSQL\16\bin\psql.exe" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] PostgreSQL 16 not found at default location.
    echo Please install PostgreSQL 16 from https://www.postgresql.org/download/windows/
    echo Then run this setup again.
    pause
    exit /b 1
)
echo [OK] PostgreSQL found.

:: ── Create .env if not exists ─────────────────────────────────
echo.
if not exist "backend\config\.env" (
    echo Creating .env file from template...
    copy "backend\config\.env.example" "backend\config\.env" >nul
    echo [ACTION NEEDED] Open backend\config\.env and set your PostgreSQL password.
    echo Default password used: postgres
    :: Set default password automatically
    powershell -Command "(Get-Content 'backend\config\.env') -replace 'your_postgres_password_here','postgres' -replace 'your_secret_key_here','arthsathi_secret_key_2026' | Set-Content 'backend\config\.env'"
    echo [OK] .env file created with default values.
) else (
    echo [OK] .env file already exists.
)

:: ── Create database and tables ────────────────────────────────
echo.
echo Setting up database...
set PGPASSWORD=postgres
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE arthsathi;" >nul 2>&1
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d arthsathi -f "database\schema.sql" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Database setup may have had issues. If arthsathi DB already exists, this is fine.
) else (
    echo [OK] Database and tables created.
)

:: ── Run ML model parser if processed CSV doesn't exist ────────
echo.
if not exist "ml-model\schemes_processed.csv" (
    echo Processing schemes dataset - this may take a minute...
    cd ml-model
    python parse_schemes.py
    cd ..
    echo [OK] Dataset processed.
) else (
    echo [OK] Processed dataset already exists.
)

echo.
echo ============================================
echo   Setup Complete!
echo   Run start.bat to launch ArthSathi.
echo ============================================
echo.
pause
