@echo off
echo Starting Celery Worker for University Visitor System (Windows)...
echo.

REM Переходим в директорию проекта (где находится manage.py)
cd /d "%~dp0visitor_system"

REM Устанавливаем модуль настроек по умолчанию (если не задан)
if "%DJANGO_SETTINGS_MODULE%"=="" set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

REM На Windows используем пул solo и concurrency=1
REM Требуется запущенный Redis. Если Redis работает в Docker, убедитесь, что порт 6379 проброшен (docker-compose.yml)

poetry run celery -A visitor_system worker --loglevel=info --pool=solo --concurrency=1

pause
