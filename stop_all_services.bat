@echo off
REM Stop all services: Redis, PostgreSQL, Celery workers
echo ========================================
echo Stopping All Services
echo ========================================
echo.

echo Stopping Celery workers...
tasklist | findstr celery >nul
if %errorlevel% equ 0 (
    echo Found Celery processes, stopping...
    taskkill /F /IM celery.exe 2>nul
    taskkill /F /FI "WINDOWTITLE eq celery*" 2>nul
    echo ✅ Celery workers stopped
) else (
    echo ℹ️ No Celery workers running
)

echo.
echo Stopping Redis Docker container...
docker ps | findstr redis_celery >nul
if %errorlevel% equ 0 (
    docker stop redis_celery
    echo ✅ Redis stopped
) else (
    echo ℹ️ Redis not running
)

echo.
echo Stopping PostgreSQL Docker container...
docker ps | findstr postgres_visitor >nul
if %errorlevel% equ 0 (
    docker stop postgres_visitor
    echo ✅ PostgreSQL stopped
) else (
    echo ℹ️ PostgreSQL not running
)

echo.
echo ========================================
echo All services stopped
echo ========================================
pause
