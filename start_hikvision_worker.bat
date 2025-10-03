@echo off
REM ============================================================
REM Celery Worker для HikVision Integration
REM ============================================================
REM Этот скрипт запускает Celery worker для обработки задач
REM интеграции с HikCentral (регистрация гостей, загрузка фото)
REM ============================================================

title Celery Worker - HikVision Queue

echo.
echo ============================================================
echo   CELERY WORKER - HIKVISION INTEGRATION
echo ============================================================
echo.
echo Запускается worker для обработки задач:
echo   - enroll_face_task (регистрация гостей + фото)
echo   - assign_access_level_task (назначение прав доступа)
echo   - revoke_access_task (отзыв доступа)
echo   - monitor_guest_passages_task (мониторинг проходов)
echo.
echo ============================================================
echo.

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

REM Проверяем что Redis запущен
echo [1/3] Проверка Redis...
docker ps | findstr redis >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Redis не запущен!
    echo Запустите Redis командой:
    echo   docker-compose up -d redis
    echo.
    pause
    exit /b 1
)
echo [OK] Redis запущен

REM Проверяем что PostgreSQL запущен
echo [2/3] Проверка PostgreSQL...
docker ps | findstr postgres >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] PostgreSQL не запущен в Docker
    echo Если используете локальный PostgreSQL - игнорируйте
    echo Если нужен Docker PostgreSQL:
    echo   docker-compose up -d db
    echo.
)

REM Запускаем Celery worker
echo [3/3] Запуск Celery Worker...
echo.
echo ============================================================
echo   WORKER ЗАПУЩЕН
echo ============================================================
echo.
echo Queue: hikvision
echo Pool: solo (для Windows)
echo Log level: info
echo.
echo Для остановки: Ctrl+C
echo ============================================================
echo.

REM Запуск с правильными параметрами для Windows
poetry run celery -A visitor_system.celery:app worker ^
    -Q hikvision ^
    --pool=solo ^
    --loglevel=info ^
    --logfile=celery_hikvision.log ^
    --pidfile=celery_hikvision.pid

REM Если worker упал, показываем сообщение
echo.
echo ============================================================
echo   WORKER ОСТАНОВЛЕН
echo ============================================================
echo.
echo Проверьте логи:
echo   celery_hikvision.log
echo   celery_hikvision_error.log
echo.
pause
