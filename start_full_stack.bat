@echo off
REM ============================================================
REM Запуск полного стека для HikVision Integration
REM ============================================================
REM Этот скрипт запускает ВСЕ необходимые сервисы:
REM 1. Redis (broker для Celery)
REM 2. PostgreSQL (база данных)
REM 3. Celery Worker (обработка задач HikVision)
REM ============================================================

title Full Stack - HikVision Integration

echo.
echo ============================================================
echo   ЗАПУСК ПОЛНОГО СТЕКА
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Запуск Redis
echo [1/3] Запуск Redis...
docker-compose up -d redis
if %errorlevel% neq 0 (
    echo [ERROR] Не удалось запустить Redis
    pause
    exit /b 1
)
echo [OK] Redis запущен на localhost:6379
echo.

REM 2. Запуск PostgreSQL
echo [2/3] Запуск PostgreSQL...
docker-compose up -d db
if %errorlevel% neq 0 (
    echo [ERROR] Не удалось запустить PostgreSQL
    pause
    exit /b 1
)
echo [OK] PostgreSQL запущен на localhost:5432
echo.

REM Ждем 5 секунд чтобы сервисы запустились
echo Ожидание запуска сервисов (5 секунд)...
timeout /t 5 /nobreak >nul

REM 3. Запуск Celery Worker
echo [3/3] Запуск Celery Worker...
echo.
echo ============================================================
echo   ВСЕ СЕРВИСЫ ЗАПУЩЕНЫ
echo ============================================================
echo.
echo Redis:      localhost:6379
echo PostgreSQL: localhost:5432
echo Worker:     hikvision queue
echo.
echo Логи worker: visitor_system\celery_hikvision.log
echo.
echo Для остановки всех сервисов: Ctrl+C и запустите stop_all.bat
echo ============================================================
echo.

REM Запускаем worker в текущем окне
cd visitor_system
poetry run celery -A visitor_system.celery:app worker ^
    -Q hikvision ^
    --pool=solo ^
    --loglevel=info ^
    --logfile=celery_hikvision.log

echo.
echo Worker остановлен.
echo Для остановки Redis и PostgreSQL запустите: stop_all.bat
echo.
pause
