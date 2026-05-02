@echo off
title RAG-for-Lab Starting...
echo [1/5] Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo [2/5] Waiting for Docker to be ready...
:wait_docker
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto wait_docker
)
echo Docker is ready.

echo [3/5] Starting Ollama...
start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 3 /nobreak >nul

echo [4/5] Starting RAG-for-Lab containers...
cd /d C:\Projects\RAG-for-Lab
docker compose up -d

echo [5/5] Opening browser...
timeout /t 15 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo  RAG-for-Lab is ready.
echo  Open http://localhost:3000
echo ========================================
pause
