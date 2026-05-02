@echo off
title RAG-for-Lab
cd /d C:\Projects\RAG-for-Lab

echo Checking container status...
docker ps --filter "name=lab-rag-backend" --filter "status=running" -q > "%TEMP%\rag_check.txt" 2>nul

set /p RUNNING=<"%TEMP%\rag_check.txt"
del "%TEMP%\rag_check.txt" >nul 2>&1

if "%RUNNING%"=="" (
    echo [STATUS] Stopped. Starting RAG-for-Lab...
    call start.bat
) else (
    echo [STATUS] Running. Stopping RAG-for-Lab...
    call stop.bat
)
