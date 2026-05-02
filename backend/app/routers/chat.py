# [ROLE] チャットAPIエンドポイント（Phase 4 で SSE ストリーミングを実装する。Phase 2 では空ルーター）
# [DEPS] services/rag.py, services/embedder.py, models/db.py, core/config.py
# [CALLED_BY] main.py

from fastapi import APIRouter

router = APIRouter()
