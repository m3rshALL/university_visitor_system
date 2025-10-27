@echo off
echo ============================================================
echo   Starting Celery Beat - Task Scheduler
echo ============================================================
echo.
echo This scheduler triggers periodic tasks:
echo - Database backup (daily at 3:00)
echo - Auto-close expired visits (every 15 min)
echo - Update dashboard metrics (every 5 min)
echo - Cleanup old audit logs (daily at 2:00)
echo - Security events analysis (hourly)
echo - Daily audit report (daily at 6:00)
echo - Monitor guest passages (every 5 min)
echo.
echo ============================================================
echo.

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

REM Устанавливаем модуль настроек
if "%DJANGO_SETTINGS_MODULE%"=="" set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev

REM Устанавливаем PYTHONPATH
set PYTHONPATH=%CD%

echo Starting Celery Beat...
echo - PYTHONPATH: %PYTHONPATH%
echo - Settings: %DJANGO_SETTINGS_MODULE%
echo - Redis: localhost:6379
echo - Timezone: Asia/Almaty
echo.

REM Запускаем Celery Beat
poetry run celery -A visitor_system.celery:app beat --loglevel=info

pause

