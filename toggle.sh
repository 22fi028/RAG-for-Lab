#!/bin/bash
# 役割: lab-rag-backend の稼働状態を見て start/stop を切り替える Linux/Mac 用スクリプト
# 動作: コンテナが running なら stop.sh、停止していれば start.sh を呼ぶ（toggle.bat と同等）

cd "$(dirname "$0")"

echo "Checking container status..."
RUNNING=$(docker ps --filter "name=lab-rag-backend" --filter "status=running" -q)

if [ -z "$RUNNING" ]; then
    echo "[STATUS] Stopped. Starting RAG-for-Lab..."
    bash "$(dirname "$0")/start.sh"
else
    echo "[STATUS] Running. Stopping RAG-for-Lab..."
    bash "$(dirname "$0")/stop.sh"
fi
