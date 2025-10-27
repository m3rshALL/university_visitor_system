@echo off
echo ============================================================
echo   Starting ALL Celery Services
echo ============================================================
echo.
echo This will start:
echo 1. Celery Worker (default queue) - for general tasks
echo 2. Celery Worker (hikvision queue) - for HikVision integration
echo 3. Celery Beat (scheduler) - for periodic tasks
echo.
echo NOTE: Each service will run in a separate window
echo Close any window to stop that service
echo.
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Запуск Celery Worker (default queue)
echo [1/3] Starting Celery Worker (default queue)...
start "Celery Worker - Default" /MIN cmd /c start_celery_default.bat
timeout /t 2 /nobreak >nul

REM 2. Запуск Celery Worker (hikvision queue)
echo [2/3] Starting Celery Worker (hikvision queue)...
start "Celery Worker - HikVision" /MIN cmd /c start_celery_hikvision_worker.bat
timeout /t 2 /nobreak >nul

REM 3. Запуск Celery Beat (scheduler)
echo [3/3] Starting Celery Beat (scheduler)...
start "Celery Beat - Scheduler" /MIN cmd /c start_celery_beat.bat
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo   ALL SERVICES STARTED
echo ============================================================
echo.
echo Check the separate windows for logs:
echo - Celery Worker - Default
echo - Celery Worker - HikVision
echo - Celery Beat - Scheduler
echo.
echo To stop all services: close all Celery windows
echo.
echo Checking health in 5 seconds...
timeout /t 5 /nobreak >nul

REM Проверка health
echo.
echo Health Check:
curl http://localhost:8000/health/
echo.

pause

