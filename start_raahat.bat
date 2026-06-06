@echo off
setlocal EnableDelayedExpansion
title RAAHAT Launcher

echo =====================================
echo          RAAHAT SMART LAUNCHER
echo =====================================
echo.

:: Move to project directory
cd /d "%~dp0"

:: ---------------------------------------------------
:: Check Docker Desktop
:: ---------------------------------------------------

tasklist | find /I "Docker Desktop.exe" >nul

if errorlevel 1 (
    echo Docker Desktop is not running.
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    echo Waiting for Docker engine...
    :waitdocker
    timeout /t 5 >nul
    docker info >nul 2>&1
    if errorlevel 1 (
        echo Docker not ready yet...
        goto waitdocker
    )
) else (
    echo Docker Desktop already running.
)

echo.
echo Starting containers...
docker compose up -d

echo.
echo Waiting for application...
timeout /t 5 >nul

echo.
echo Starting Cloudflare Quick Tunnel...

start "Cloudflare Tunnel" cmd /k ^
cloudflared tunnel --url http://localhost:8000

echo.
echo =====================================
echo.
echo Docker started.
echo Tunnel window launched.
echo.
echo Copy the trycloudflare URL from the
echo Cloudflare window and paste it into
echo Supabase until raahat.eu.org is approved.
echo.
echo =====================================

start http://localhost:8000

pause