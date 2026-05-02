# [ROLE] FastAPI アプリケーションのエントリーポイント・起動時の埋め込みモデルウォームアップ
# [DEPS] core/config.py, models/db.py, services/embedder.py, routers/*
# [CALLED_BY] uvicorn（Dockerfile CMD）

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.db import Base, engine
from app.routers import chat, conversations, documents
from app.services.embedder import get_embedder


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: 埋め込みモデルをロードしてウォームアップ
    # multilingual-e5-large のロードに 10〜30 秒かかるため
    # 起動完了前に質問が来るとエラーになるのを防ぐ
    print("Loading embedding model...")
    embedder = get_embedder()
    embedder.encode(["warmup"])
    print("Embedding model ready.")
    yield


app = FastAPI(title="研究室特化型RAG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(documents.router, prefix="/api", tags=["documents"])


@app.get("/health")
def health():
    try:
        get_embedder()
        embedding_status = "ready"
    except Exception:
        embedding_status = "loading"
    return {"status": "ok", "embedding_model": embedding_status}
