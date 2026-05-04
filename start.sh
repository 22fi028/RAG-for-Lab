#!/bin/bash
# 役割: RAG-for-Lab を Linux/Mac で起動するワンクリック相当のスクリプト
# 前提: Ollama はホストで起動済み（ollama serve）

set -e

echo "[1/4] Checking Ollama..."
if ! curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "WARNING: Ollama is not running. Start it with: ollama serve"
fi

echo "[2/4] Starting RAG-for-Lab containers..."
cd "$(dirname "$0")"
docker compose up -d

echo "[3/4] Waiting for containers to be ready..."
sleep 15

echo "[4/4] Done."
echo "========================================"
echo " RAG-for-Lab is ready."
echo " Open http://localhost:3000"
echo "========================================"
