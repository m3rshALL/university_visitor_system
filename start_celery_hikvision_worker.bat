@echo off
REM Start Celery Worker for HikVision Integration Queue
echo ========================================
echo Starting Celery Worker for HikVision
echo ========================================
echo.

REM Check if Redis is running
docker ps | findstr redis_celery >nul
if %errorlevel% neq 0 (
    echo ❌ Redis is not running!
    echo Please start Redis first with: start_redis_docker.bat
    pause
    exit /b 1
)

REM Check if PostgreSQL is running
docker ps | findstr postgres_visitor >nul
if %errorlevel% neq 0 (
    echo ⚠️ Warning: PostgreSQL is not running!
    echo Please start PostgreSQL with: start_postgres_docker.bat
    echo.
)

echo ✅ Redis is running
echo.

cd /d "%~dp0visitor_system"

REM Set Django settings module
set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

REM Check if .env exists
if not exist ".env" (
    echo ⚠️ Warning: .env file not found in visitor_system directory
    echo Please create .env from .env.example
    pause
    exit /b 1
)

echo Starting Celery worker...
echo Queue: hikvision
echo Pool: solo (Windows compatible)
echo.

REM Start worker with solo pool for Windows compatibility
poetry run celery -A visitor_system.celery:app worker ^
    -Q hikvision ^
    --pool=solo ^
    --loglevel=info ^
    --logfile=celery_hikvision.log ^
    -n hikvision_worker@%%h

REM If worker exits
echo.
echo ⚠️ Celery worker stopped
pause
