# [ROLE] ChromaDB検索・プロンプト組み立て・OllamaへのLLMストリーミング呼び出し
# [DEPS] core/config.py, core/retry.py, services/embedder.py
# [CALLED_BY] routers/chat.py

import asyncio
import json
from typing import AsyncGenerator

import chromadb
import httpx

from app.core.config import settings


SYSTEM_PROMPT = (
    "あなたは研究室の知識ベースアシスタントです。\n"
    "与えられたコンテキストのみを根拠として回答してください。\n"
    "コンテキストに情報がない場合は「該当する情報が見つかりませんでした」と答えてください。\n"
    "回答は日本語で行ってください。\n"
    "回答の末尾に【参照】を付ける必要はありません。根拠の表示はシステムが自動で行います。\n"
    "/no_think"
)


async def search_chroma(query_embedding: list[float]) -> list[dict]:
    """
    ChromaDB を Top-K で検索し similarity_threshold 以上のチャンクを返す。
    最大2回リトライ（指数バックオフ）。全失敗時は空リストで LLM 続行。
    """
    for attempt in range(2):
        try:
            client = chromadb.PersistentClient(path=settings.chroma_path)
            collection = client.get_or_create_collection(settings.chroma_collection)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=settings.rag_top_k,
                include=["documents", "metadatas", "distances"],
            )
            chunks: list[dict] = []
            documents = results.get("documents") or [[]]
            metadatas = results.get("metadatas") or [[]]
            distances = results.get("distances") or [[]]
            if not documents or not documents[0]:
                return []
            for doc, meta, dist in zip(documents[0], metadatas[0], distances[0]):
                score = 1 - dist
                if score >= settings.rag_similarity_threshold:
                    chunks.append({"content": doc, "score": score, "metadata": meta or {}})
            return chunks
        except Exception as e:
            if attempt == 1:
                print(f"ChromaDB search failed: {e}")
                return []
            await asyncio.sleep(settings.pipeline_base_delay)
    return []


def build_context_blocks(chunks: list[dict]) -> str:
    """検索チャンクをプロンプト用 context_blocks 形式に整形する。"""
    if not chunks:
        return "(コンテキストなし)"
    lines: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata") or {}
        title = meta.get("title", "") or "(タイトル不明)"
        chapter = meta.get("chapter", "") or "-"
        page = meta.get("page_num", 0) or 0
        lines.append(f"[{i}] {chunk['content']}")
        lines.append(f"出典: {title} / {chapter} / p.{page}")
    return "\n".join(lines)


def build_history_text(history: list[dict]) -> str:
    """直近 settings.rag_history_window 件の履歴を整形する。history は古い順の dict 配列。"""
    if not history:
        return "(履歴なし)"
    window = history[-settings.rag_history_window:]
    lines: list[str] = []
    for msg in window:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else "(履歴なし)"


def build_prompt(question: str, chunks: list[dict], history: list[dict]) -> str:
    """Ollama に渡す最終プロンプトを組み立てる。"""
    context_blocks = build_context_blocks(chunks)
    history_text = build_history_text(history)
    return (
        f"System:\n{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"History:\n{history_text}\n\n"
        f"Question:\n{question}\n"
    )


def build_sources_from_chunks(chunks: list[dict]) -> list[dict]:
    """ChromaDB 検索結果メタデータから根拠リストを生成する（重複除去）。"""
    sources: list[dict] = []
    seen: set = set()
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        title = meta.get("title", "") or ""
        chapter = meta.get("chapter", "") or ""
        page = meta.get("page_num", 0) or 0
        key = (title, chapter, page)
        if key not in seen:
            seen.add(key)
            sources.append({"title": title, "chapter": chapter, "page": page})
    return sources


async def stream_llm(prompt: str) -> AsyncGenerator[str, None]:
    """
    Ollama /api/generate へストリーミングリクエストを投げ、トークンを yield する。
    async generator なので @with_retry は使えない。リトライは関数内ループで実装する。
    Qwen3 thinking mode 対策として options.think=False を渡す。
    """
    max_attempts = settings.pipeline_max_retry
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": True,
                        "think": False,
                        "options": {
                            "temperature": settings.rag_temperature,
                            "num_predict": settings.rag_max_tokens,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            return
            return
        except Exception as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(settings.pipeline_base_delay * (2 ** attempt))
    if last_error is not None:
        raise last_error
