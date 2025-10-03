@echo off
REM ============================================================
REM Проверка статуса всех сервисов
REM ============================================================

title Service Status Check

echo.
echo ============================================================
echo   ПРОВЕРКА СТАТУСА СЕРВИСОВ
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Проверка Docker контейнеров
echo [Docker Containers]
echo ============================================================
docker-compose ps
echo.

REM 2. Проверка Celery Workers
echo [Celery Workers]
echo ============================================================
tasklist | findstr celery.exe
if %errorlevel% equ 0 (
    echo [OK] Celery worker запущен
) else (
    echo [WARNING] Celery worker НЕ запущен
)
echo.

REM 3. Проверка Redis
echo [Redis Connection]
echo ============================================================
docker exec -it university_visitor_system-redis-1 redis-cli ping 2>nul
if %errorlevel% equ 0 (
    echo [OK] Redis отвечает
) else (
    echo [ERROR] Redis не отвечает
)
echo.

REM 4. Проверка PostgreSQL
echo [PostgreSQL Connection]
echo ============================================================
docker exec -it university_visitor_system-db-1 pg_isready -U visitor_user 2>nul
if %errorlevel% equ 0 (
    echo [OK] PostgreSQL готов
) else (
    echo [ERROR] PostgreSQL не готов
)
echo.

REM 5. Проверка логов Celery
echo [Recent Celery Logs]
echo ============================================================
if exist "visitor_system\celery_hikvision.log" (
    echo Последние 10 строк celery_hikvision.log:
    powershell -Command "Get-Content visitor_system\celery_hikvision.log -Tail 10"
) else (
    echo [WARNING] Лог файл не найден
)
echo.

REM 6. Проверка задач в очереди
echo [Celery Queue Status]
echo ============================================================
cd visitor_system
poetry run celery -A visitor_system.celery:app inspect active 2>nul
if %errorlevel% equ 0 (
    echo.
    echo [OK] Статус очереди получен
) else (
    echo [ERROR] Не удалось получить статус очереди
)
cd ..

echo.
echo ============================================================
echo   ПРОВЕРКА ЗАВЕРШЕНА
echo ============================================================
echo.
pause
