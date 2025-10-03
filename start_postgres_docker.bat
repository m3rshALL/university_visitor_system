@echo off
REM Start PostgreSQL Docker container
echo Starting PostgreSQL Docker container...

docker ps -a | findstr postgres_visitor >nul
if %errorlevel% equ 0 (
    echo PostgreSQL container exists, starting...
    docker start postgres_visitor
) else (
    echo Creating and starting PostgreSQL container...
    docker run -d --name postgres_visitor ^
        -e POSTGRES_DB=visitor_system ^
        -e POSTGRES_USER=visitor_user ^
        -e POSTGRES_PASSWORD=visitor_pass ^
        -p 5432:5432 ^
        postgres:15-alpine
)

echo.
echo Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak >nul

docker ps | findstr postgres_visitor
if %errorlevel% equ 0 (
    echo.
    echo ✅ PostgreSQL is running on localhost:5432
    echo.
    echo Database: visitor_system
    echo User: visitor_user
    echo Password: visitor_pass
    echo.
    echo Test connection with: psql -h localhost -U visitor_user -d visitor_system
) else (
    echo ❌ PostgreSQL failed to start
    exit /b 1
)

pause
