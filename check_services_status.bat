@echo off
REM Check status of all services
echo ========================================
echo Service Status Check
echo ========================================
echo.

echo [1] Redis Status:
docker ps | findstr redis_celery >nul
if %errorlevel% equ 0 (
    echo ✅ Redis is RUNNING
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr redis_celery
) else (
    echo ❌ Redis is NOT RUNNING
)

echo.
echo [2] PostgreSQL Status:
docker ps | findstr postgres_visitor >nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL is RUNNING
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr postgres_visitor
) else (
    echo ❌ PostgreSQL is NOT RUNNING
)

echo.
echo [3] Celery Workers:
tasklist | findstr celery >nul
if %errorlevel% equ 0 (
    echo ✅ Celery workers are RUNNING
    tasklist | findstr celery
) else (
    echo ❌ No Celery workers running
)

echo.
echo [4] Redis Connection Test:
docker ps | findstr redis_celery >nul
if %errorlevel% equ 0 (
    docker exec redis_celery redis-cli ping
    if %errorlevel% equ 0 (
        echo ✅ Redis responding to PING
    )
) else (
    echo ⚠️ Redis not running, skipping connection test
)

echo.
echo ========================================
echo Status check complete
echo ========================================
pause
