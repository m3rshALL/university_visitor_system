param(
    [Parameter(Mandatory=$false)]
    [string]$TunnelDomain = "",
    [Parameter(Mandatory=$false)]
    [ValidateSet("ngrok", "localtunnel", "serveo")]
    [string]$TunnelType = "ngrok"
)

Write-Host "🚀 Запуск Django с поддержкой туннелей..." -ForegroundColor Green

# Если домен не указан, используем wildcard для ngrok
if (-not $TunnelDomain) {
    Write-Host "⚠️  Домен не указан. Используется поддержка всех ngrok доменов." -ForegroundColor Yellow
    $env:NGROK_DOMAIN = ""
} else {
    $env:NGROK_DOMAIN = $TunnelDomain
    Write-Host "🌐 Установлен домен: $TunnelDomain" -ForegroundColor Cyan
}

# Переходим в директорию проекта
Set-Location -Path (Join-Path $PSScriptRoot "visitor_system")

# Проверяем, что Docker контейнеры запущены
Write-Host "🐳 Проверка Docker контейнеров..." -ForegroundColor Blue
$containers = docker-compose ps --services --filter "status=running"
if ($containers -notcontains "db" -or $containers -notcontains "redis") {
    Write-Host "⚠️  Запускаю базу данных и Redis..." -ForegroundColor Yellow
    Set-Location ..
    docker-compose up -d db redis
    Start-Sleep 5
    Set-Location visitor_system
}

# Проверяем конфигурацию
Write-Host "🔧 Проверка конфигурации Django..." -ForegroundColor Blue
$checkResult = & poetry run python manage.py check --deploy 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка в конфигурации Django!" -ForegroundColor Red
    Write-Host $checkResult -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "✅ Конфигурация проверена успешно!" -ForegroundColor Green
Write-Host ""

# Показываем инструкции для разных туннелей
Write-Host "📡 Инструкции для запуска туннеля:" -ForegroundColor Magenta
Write-Host ""

switch ($TunnelType) {
    "ngrok" {
        Write-Host "🔗 NGROK:" -ForegroundColor Cyan
        Write-Host "   ngrok http http://localhost:8000" -ForegroundColor White
        Write-Host "   Для регистрации: https://ngrok.com/signup" -ForegroundColor Gray
    }
    "localtunnel" {
        Write-Host "🔗 LOCALTUNNEL:" -ForegroundColor Cyan
        Write-Host "   npm install -g localtunnel" -ForegroundColor White
        Write-Host "   lt --port 8000 --subdomain myapp" -ForegroundColor White
    }
    "serveo" {
        Write-Host "🔗 SERVEO:" -ForegroundColor Cyan
        Write-Host "   ssh -R 80:localhost:8000 serveo.net" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "👤 Доступные суперпользователи для входа:" -ForegroundColor Magenta
Write-Host "   • sako (maroccocombo@gmail.com)" -ForegroundColor Cyan
Write-Host "   • admin (admin@admin.kz)" -ForegroundColor Cyan
Write-Host "   • Sako (sako@sako.kz)" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 Запуск сервера на 0.0.0.0:8000..." -ForegroundColor Green
Write-Host "💡 Совет: При ошибке ngrok ERR_NGROK_734 - перезапустите ngrok для нового домена" -ForegroundColor Yellow
Write-Host ""

# Запускаем сервер
& poetry run python manage.py runserver 0.0.0.0:8000
