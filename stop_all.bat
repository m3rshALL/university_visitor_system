@echo off
REM ============================================================
REM Остановка всех сервисов HikVision Integration
REM ============================================================

title Stopping All Services

echo.
echo ============================================================
echo   ОСТАНОВКА ВСЕХ СЕРВИСОВ
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Остановка Celery Workers
echo [1/3] Остановка Celery Workers...
taskkill /F /IM celery.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Celery Worker*" >nul 2>&1
echo [OK] Celery workers остановлены

REM 2. Остановка Docker контейнеров
echo [2/3] Остановка Docker контейнеров...
docker-compose stop redis db
echo [OK] Redis и PostgreSQL остановлены

REM 3. Опционально: удалить контейнеры
echo.
echo Хотите удалить контейнеры (не только остановить)? (Y/N)
set /p REMOVE="Удалить контейнеры? "
if /i "%REMOVE%"=="Y" (
    docker-compose down
    echo [OK] Контейнеры удалены
)

echo.
echo ============================================================
echo   ВСЕ СЕРВИСЫ ОСТАНОВЛЕНЫ
echo ============================================================
echo.
pause
