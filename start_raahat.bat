@echo off
setlocal
title RAAHAT Launcher

echo =====================================
echo         RAAHAT SMART LAUNCHER
echo =====================================
echo.

cd /d "%~dp0"

:: ---------------------------------------
:: Build React Frontend
:: ---------------------------------------
echo Building React Frontend...
where npm >nul 2>&1
if errorlevel 1 (
    echo [WARNING] npm not found. Skipping local frontend compilation.
    echo Make sure you have Node.js installed to build the frontend.
) else (
    cd frontend
    call npm run build
    cd ..
)
echo.


:: ---------------------------------------
:: Ensure Docker Desktop is running
:: ---------------------------------------

docker info >nul 2>&1

if errorlevel 1 (
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    :waitdocker
    timeout /t 5 >nul
    docker info >nul 2>&1

    if errorlevel 1 (
        echo Waiting for Docker...
        goto waitdocker
    )
)

echo Docker is ready.
echo.

:: ---------------------------------------
:: Start containers if not running
:: ---------------------------------------

echo Starting RAAHAT containers...
docker compose up -d

echo.
echo Waiting for API...
timeout /t 3 >nul

:: ---------------------------------------
:: Start Cloudflare tunnel
:: ---------------------------------------

echo Starting Cloudflare Tunnel...

start "Cloudflare Tunnel" cmd /k cloudflared tunnel --url http://localhost:8000

echo.
echo Opening browser...
start http://localhost:8000

echo.
echo =====================================
echo RAAHAT is running.
echo =====================================

pause