@echo off
title RAG-for-Lab Stopping...
echo Stopping containers...
cd /d C:\Projects\RAG-for-Lab
docker compose down
echo.
echo RAG-for-Lab has been stopped.
pause
