@echo off
echo Запуск Django с поддержкой ngrok...

REM Устанавливаем переменные окружения для ngrok
set NGROK_DOMAIN=%1
if "%NGROK_DOMAIN%"=="" (
    echo Использование: start_with_ngrok.bat [ngrok_domain]
    echo Пример 1: start_with_ngrok.bat https://a006f6aa4edc.ngrok-free.app
    echo Пример 2: start_with_ngrok.bat a006f6aa4edc.ngrok-free.app
    echo.
    echo ====================================================================
    echo ВАЖНО! Для корректной работы запустите ngrok с флагом --host-header:
    echo   ngrok http 8000 --host-header="localhost:8000"
    echo.
    echo Или используйте короткую форму:
    echo   ngrok http 8000 --host-header=localhost:8000
    echo ====================================================================
    echo.
    echo Затем скопируйте URL из вывода ngrok и передайте его этому скрипту.
    pause
    exit /b 1
)

REM Убираем схему (http:// или https://) если она есть
set NGROK_DOMAIN=%NGROK_DOMAIN:https://=%
set NGROK_DOMAIN=%NGROK_DOMAIN:http://=%

echo Установлен ngrok домен: %NGROK_DOMAIN%

REM Отключаем SSL редирект и CSRF проверку для ngrok
set DJANGO_SETTINGS_MODULE=visitor_system.conf.dev
set USE_X_FORWARDED_HOST=True

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

echo.
echo ===================================================
echo ВАЖНО: Настройки для ngrok:
echo - NGROK_DOMAIN: %NGROK_DOMAIN%
echo - Django работает на 0.0.0.0:8000
echo - Убедитесь, что ngrok проброшен на порт 8000
echo ===================================================
echo.

REM Не проверяем deploy конфигурацию в dev режиме с ngrok
echo Запуск сервера на 0.0.0.0:8000...
echo.
poetry run python manage.py runserver 0.0.0.0:8000
