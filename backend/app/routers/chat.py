# [ROLE] チャットAPIエンドポイント・SSEストリーミングレスポンスの送出
# [DEPS] services/rag.py, services/embedder.py, models/db.py, core/config.py
# [CALLED_BY] main.py

import json
from uuid import UUID

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import Conversation, Message, SessionLocal
from app.services.embedder import embed_query
from app.services.rag import (
    build_prompt,
    build_sources_from_chunks,
    search_chroma,
    stream_llm,
)


router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: UUID
    question: str


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _load_history(db: Session, conversation_id: UUID) -> list[dict]:
    """直近の履歴を古い順の dict 配列で取得する。"""
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in msgs]


def _save_messages(
    db: Session,
    conversation_id: UUID,
    question: str,
    answer: str,
    sources: list[dict],
) -> None:
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=question,
        sources=None,
    )
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=sources or None,
    )
    db.add(user_msg)
    db.add(assistant_msg)


async def generate_stream(req: ChatRequest):
    # 履歴取得・埋め込み・検索・プロンプト組み立ては try の外でも内でも可だが、
    # ここから先のエラーはすべて SSE error イベントで通知する。
    try:
        db = SessionLocal()
        try:
            conv = (
                db.query(Conversation)
                .filter(Conversation.id == req.conversation_id)
                .first()
            )
            if not conv:
                yield _sse({"type": "error", "message": "会話が見つかりません。"})
                return
            history = _load_history(db, req.conversation_id)
        finally:
            db.close()

        query_embedding = embed_query(req.question)
        chunks = await search_chroma(query_embedding)
        prompt = build_prompt(req.question, chunks, history)

        full_response = ""
        async for token in stream_llm(prompt):
            full_response += token
            yield _sse({"type": "token", "content": token})

        sources = build_sources_from_chunks(chunks)
        yield _sse({"type": "done", "sources": sources})

        # ストリーミング内の DB 保存は SessionLocal() を直接使用する（next(get_db()) は不可）
        session = SessionLocal()
        try:
            _save_messages(
                session,
                req.conversation_id,
                req.question,
                full_response,
                sources,
            )
            session.commit()
        finally:
            session.close()

    except httpx.ConnectError:
        yield _sse({
            "type": "error",
            "message": "Ollama に接続できません。Ollama が起動しているか確認してください。",
        })
    except httpx.TimeoutException:
        yield _sse({
            "type": "error",
            "message": "回答生成がタイムアウトしました。もう一度試してください。",
        })
    except Exception as e:
        yield _sse({
            "type": "error",
            "message": f"エラーが発生しました: {str(e)}",
        })


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        generate_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
