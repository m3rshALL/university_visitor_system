@echo off
REM Скрипт для проверки credentials HikCentral Professional
echo ========================================
echo Проверка HikCentral Credentials
echo ========================================
echo.

poetry run python check_hikcentral_credentials.py
pause

