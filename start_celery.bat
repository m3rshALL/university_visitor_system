@echo off
echo Starting Celery Worker for University Visitor System...
echo.

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

REM Активируем виртуальное окружение Poetry и запускаем Celery
poetry run celery -A visitor_system worker --loglevel=info --concurrency=2

pause
