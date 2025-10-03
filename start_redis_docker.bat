@echo off
REM Start Redis Docker container for Celery broker/backend
echo Starting Redis Docker container...

docker ps -a | findstr redis_celery >nul
if %errorlevel% equ 0 (
    echo Redis container exists, starting...
    docker start redis_celery
) else (
    echo Creating and starting Redis container...
    docker run -d --name redis_celery -p 6379:6379 redis:alpine
)

echo.
echo Waiting for Redis to be ready...
timeout /t 3 /nobreak >nul

docker ps | findstr redis_celery
if %errorlevel% equ 0 (
    echo.
    echo ✅ Redis is running on localhost:6379
    echo.
    echo Test connection with: redis-cli ping
) else (
    echo ❌ Redis failed to start
    exit /b 1
)

pause
