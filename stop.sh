#!/bin/bash
# 役割: RAG-for-Lab のコンテナを停止する Linux/Mac 用スクリプト

cd "$(dirname "$0")"
echo "Stopping containers..."
docker compose down
echo "RAG-for-Lab has been stopped."
