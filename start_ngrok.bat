@echo off
echo ====================================================================
echo Запуск ngrok с правильными параметрами для Django
echo ====================================================================
echo.
echo Этот скрипт запустит ngrok с флагом --host-header для правильной
echo работы с Django. После запуска скопируйте URL и используйте его
echo в start_with_ngrok.bat
echo.
echo ====================================================================
echo.

REM Проверяем, установлен ли ngrok
where ngrok >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ОШИБКА: ngrok не найден в PATH!
    echo.
    echo Пожалуйста, установите ngrok:
    echo 1. Скачайте с https://ngrok.com/download
    echo 2. Распакуйте в папку (например, C:\ngrok)
    echo 3. Добавьте папку в PATH или запустите из той же папки
    echo.
    echo Или запустите ngrok вручную:
    echo   cd C:\path\to\ngrok
    echo   .\ngrok http 8000 --host-header=localhost:8000
    echo.
    pause
    exit /b 1
)

echo Запускаем ngrok...
echo.
echo ВАЖНО: После запуска скопируйте URL (например, https://xxxx.ngrok-free.app)
echo и используйте его в start_with_ngrok.bat:
echo   .\start_with_ngrok.bat https://xxxx.ngrok-free.app
echo.
echo ====================================================================
echo.

ngrok http 8000 --host-header=localhost:8000
