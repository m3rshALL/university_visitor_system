@echo off
echo Запуск Django с поддержкой ngrok...

REM Устанавливаем переменные окружения для ngrok
set NGROK_DOMAIN=%1
if "%NGROK_DOMAIN%"=="" (
    echo Использование: start_with_ngrok.bat https://5f03124ff1b7.ngrok-free.app/
    echo Пример: start_with_ngrok.bat 5f03124ff1b7.ngrok-free.app
    exit /b 1
)

echo Установлен ngrok домен: %NGROK_DOMAIN%

REM Переходим в директорию проекта
cd /d "%~dp0visitor_system"

REM Проверяем конфигурацию
echo Проверка конфигурации Django...
poetry run python manage.py check --deploy
if %ERRORLEVEL% neq 0 (
    echo Ошибка в конфигурации Django!
    pause
    exit /b 1
)

echo Запуск сервера на 0.0.0.0:8000...
echo Теперь можете запустить ngrok в другом терминале: ngrok http http://localhost:8000
echo.
poetry run python manage.py runserver 0.0.0.0:8000
