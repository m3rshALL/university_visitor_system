param(
    [Parameter(Mandatory=$true)]
    [string]$NgrokDomain
)

Write-Host "Запуск Django с поддержкой ngrok..." -ForegroundColor Green

# Устанавливаем переменную окружения для ngrok
$env:NGROK_DOMAIN = $NgrokDomain
Write-Host "Установлен ngrok домен: $NgrokDomain" -ForegroundColor Yellow

# Переходим в директорию проекта
Set-Location -Path (Join-Path $PSScriptRoot "visitor_system")

# Проверяем конфигурацию
Write-Host "Проверка конфигурации Django..." -ForegroundColor Blue
$checkResult = & poetry run python manage.py check --deploy 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка в конфигурации Django!" -ForegroundColor Red
    Write-Host $checkResult -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "Конфигурация проверена успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "Запуск сервера на 0.0.0.0:8000..." -ForegroundColor Blue
Write-Host "Теперь можете запустить ngrok в другом терминале:" -ForegroundColor Yellow
Write-Host "ngrok http http://localhost:8000" -ForegroundColor Cyan
Write-Host ""

# Показываем информацию о пользователях
Write-Host "Доступные суперпользователи для входа:" -ForegroundColor Magenta
Write-Host "- sako (maroccocombo@gmail.com)" -ForegroundColor Cyan
Write-Host "- admin (admin@admin.kz)" -ForegroundColor Cyan
Write-Host "- Sako (sako@sako.kz)" -ForegroundColor Cyan
Write-Host ""

# Запускаем сервер
& poetry run python manage.py runserver 0.0.0.0:8000
