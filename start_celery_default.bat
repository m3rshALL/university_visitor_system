@echo off
echo ============================================================
echo   Starting Celery Worker - Default Queue
echo ============================================================
echo.
echo This worker handles:
echo - Database backups
echo - Auto-close expired visits
echo - Audit reports
echo - Daily summaries
echo - All general tasks
echo.
echo ============================================================
echo.

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

REM Устанавливаем модуль настроек
if "%DJANGO_SETTINGS_MODULE%"=="" set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

REM Устанавливаем PYTHONPATH
set PYTHONPATH=%CD%

echo Starting Celery Worker...
echo - PYTHONPATH: %PYTHONPATH%
echo - Settings: %DJANGO_SETTINGS_MODULE%
echo - Redis: localhost:6379
echo - Queue: default (celery)
echo - Pool: solo (Windows compatible)
echo.

REM Запускаем worker для default очереди
poetry run celery -A visitor_system.celery:app worker --pool=solo --loglevel=info

pause

