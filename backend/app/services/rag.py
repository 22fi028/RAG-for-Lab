# [ROLE] BM25向けクエリ拡張・ハイブリッド検索（BM25 + ベクトル + RRF統合）・プロンプト組み立て・OllamaへのLLMストリーミング呼び出し・チャンク/根拠の共通型(ChunkResult/SourceItem)定義
# [DEPS] core/config.py, services/embedder.py
# [CALLED_BY] routers/chat.py, routers/documents.py（invalidate_bm25_cacheのみ）, scripts/eval_recall.py

import asyncio
import json
from typing import AsyncGenerator, TypedDict

import chromadb
import httpx
from rank_bm25 import BM25Okapi

from app.core.config import settings


class ChunkResult(TypedDict):
    """検索系関数（search_chroma / search_bm25 / hybrid_search）が返すチャンクの共通型。
    metadata は内部キー（title / chapter / page_num / doc_id 等）が任意のため dict のまま。"""
    content: str
    score: float
    metadata: dict


class SourceItem(TypedDict):
    """フロント側の Source と一致する根拠表示用の構造（build_sources_from_chunks の出力）。"""
    title: str
    chapter: str
    page: int


SYSTEM_PROMPT = (
    "あなたは研究室の知識ベースアシスタントです。\n"
    "与えられたコンテキストのみを根拠として回答してください。\n"
    "コンテキストに情報がない場合は「該当する情報が見つかりませんでした」と答えてください。\n"
    "回答は日本語で行ってください。\n"
    "回答の末尾に【参照】を付ける必要はありません。根拠の表示はシステムが自動で行います。\n"
    "/no_think"
)


async def expand_query_for_bm25(query: str) -> str:
    """
    BM25検索専用のクエリ拡張。
    LLMに「答えが書かれたチャンクに含まれていそうな固有語」を生成させ、
    "{元のquery} {拡張語}" を返す。ベクトル検索のクエリには使用しないこと。
    失敗・タイムアウト時は元のqueryをそのまま返す（フォールバック）。
    """
    prompt = (
        "/no_think\n"
        "以下の質問に答えている文書のチャンクに含まれていそうな、\n"
        "具体的な単語・数値・英語表記・略語を5語以内で列挙してください。\n"
        "汎用語（「定義」「とは」「方法」など）は除外してください。\n"
        "スペース区切りで出力し、説明文は不要です。\n\n"
        f"質問: {query}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 60,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            raw = (data.get("response") or "").strip()
            if not raw:
                return query
            # Qwen3 はしばしば説明文や同語反復を返すため、5語以内・重複なしに整形する
            first_line = raw.splitlines()[0]
            seen: set[str] = set()
            tokens: list[str] = []
            for tok in first_line.split():
                if tok not in seen:
                    seen.add(tok)
                    tokens.append(tok)
                if len(tokens) >= 5:
                    break
            if not tokens:
                return query
            return f"{query} {' '.join(tokens)}"
    except Exception as e:
        print(f"[rag] BM25 query expansion failed, falling back to original query: {e}")
        return query


async def search_chroma(query_embedding: list[float]) -> list[ChunkResult]:
    """
    ChromaDB を Top-K で検索し similarity_threshold 以上のチャンクを返す。
    最大2回リトライ（指数バックオフ）。全失敗時は空リストで LLM 続行。
    ハイブリッド検索の上流側（ベクトル検索）として hybrid_search() からも呼ばれる。
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
            chunks: list[ChunkResult] = []
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


# --- BM25 索引・ハイブリッド検索 -----------------------------------------------------------
# ChromaDB の全チャンクからメモリ上に BM25 索引を構築してキャッシュする。
# 文書追加・削除時は invalidate_bm25_cache() でキャッシュを破棄して次回検索時にリビルドする。

_bm25_index: BM25Okapi | None = None
_bm25_corpus: list[tuple[str, str, dict]] | None = None  # [(chunk_id, content, metadata), ...]


def _tokenize(text: str) -> list[str]:
    """
    文字N-gram（2-gram + 3-gram）でトークン化する。日本語のように分かち書きが
    難しい言語でも BM25 が機能するよう、文字単位の連続部分文字列を語彙として扱う。
    set() で重複排除してから list 化する。空文字や空白のみは空リストを返す。
    """
    if not text or not text.strip():
        return []
    tokens: set[str] = set()
    for n in (2, 3):
        for i in range(len(text) - n + 1):
            tokens.add(text[i:i + n])
    return list(tokens)


def build_bm25_index() -> None:
    """ChromaDBから全チャンクを取得し BM25Okapi 索引をモジュール変数にキャッシュする。"""
    global _bm25_index, _bm25_corpus
    try:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(settings.chroma_collection)
        results = collection.get(include=["documents", "metadatas"])
        ids = results.get("ids") or []
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
    except Exception as e:
        print(f"[bm25] failed to fetch chunks from ChromaDB: {e}")
        _bm25_index = None
        _bm25_corpus = None
        return

    if not documents:
        print("[bm25] no chunks found in ChromaDB; index not built")
        _bm25_index = None
        _bm25_corpus = []
        return

    corpus: list[tuple[str, str, dict]] = []
    tokenized: list[list[str]] = []
    for chunk_id, doc, meta in zip(ids, documents, metadatas):
        tokens = _tokenize(doc)
        if not tokens:
            continue
        corpus.append((chunk_id, doc, meta or {}))
        tokenized.append(tokens)

    if not tokenized:
        _bm25_index = None
        _bm25_corpus = []
        print("[bm25] all chunks tokenized to empty; index not built")
        return

    _bm25_index = BM25Okapi(tokenized)
    _bm25_corpus = corpus
    print(f"[bm25] index built with {len(corpus)} chunks")


def invalidate_bm25_cache() -> None:
    """文書追加・削除・再インデックス時に呼び出してキャッシュを破棄する。"""
    global _bm25_index, _bm25_corpus
    _bm25_index = None
    _bm25_corpus = None
    print("[bm25] cache invalidated")


def search_bm25(query: str, top_k: int) -> list[ChunkResult]:
    """
    BM25でクエリに対する上位 top_k 件を返す。
    インデックスが未構築なら build_bm25_index() を呼ぶ。
    戻り値の dict には ChunkResult のキーに加えてデバッグ用の "rank" キーを含む
    （ChunkResult は最低限のスキーマで、追加キーは runtime では許容される）。
    """
    if _bm25_index is None:
        build_bm25_index()
    if _bm25_index is None or not _bm25_corpus:
        return []

    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = _bm25_index.get_scores(tokens)
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]

    results: list[ChunkResult] = []
    for rank, (idx, score) in enumerate(indexed, start=1):
        if score <= 0:
            continue
        _, content, metadata = _bm25_corpus[idx]
        results.append({
            "content": content,
            "score": float(score),
            "metadata": metadata,
            "rank": rank,
        })
    return results


def reciprocal_rank_fusion(
    vector_results: list[ChunkResult],
    bm25_results: list[ChunkResult],
    k: int = 60,
    top_k: int | None = None,
) -> list[ChunkResult]:
    """
    RRFでベクトル検索とBM25の結果を統合する。
    各リストの順位 r から RRF スコア 1 / (k + r) を計算し、両リストのスコアを加算する。
    重複排除は (doc_id, content) をキーに行う。
    """
    if top_k is None:
        top_k = settings.rag_top_k

    rrf_scores: dict[tuple, float] = {}
    chunk_data: dict[tuple, ChunkResult] = {}

    def _key(chunk: ChunkResult) -> tuple:
        meta = chunk["metadata"]
        return (meta.get("doc_id", ""), chunk["content"])

    for rank, chunk in enumerate(vector_results, start=1):
        key = _key(chunk)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
        chunk_data[key] = chunk

    for rank, chunk in enumerate(bm25_results, start=1):
        key = _key(chunk)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
        if key not in chunk_data:
            chunk_data[key] = chunk

    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    return [chunk_data[k_] for k_ in sorted_keys[:top_k]]


async def hybrid_search_with_components(
    query: str,
    query_embedding: list[float],
    expand_bm25: bool = True,
) -> tuple[list[ChunkResult], list[ChunkResult], list[ChunkResult]]:
    """
    ベクトル検索・BM25検索・RRF統合結果の3つを返すデバッグ/評価用エントリ。
    戻り値: (vector_results, bm25_results, fused_results)
    eval_recall.py の --debug などで「BM25単体」「Vector単体」を比較したい場合に使う。
    """
    vector_results = await search_chroma(query_embedding)
    bm25_query = await expand_query_for_bm25(query) if expand_bm25 else query
    bm25_results = search_bm25(bm25_query, top_k=settings.rag_top_k * 2)
    fused = reciprocal_rank_fusion(vector_results, bm25_results)
    return vector_results, bm25_results, fused


async def hybrid_search(
    query: str,
    query_embedding: list[float],
    expand_bm25: bool = True,
) -> list[ChunkResult]:
    """
    ベクトル検索（ChromaDB）とBM25検索を実行し RRF で統合する。
    expand_bm25=True のとき BM25 クエリのみ LLM 拡張する（ベクトル側は元の query を維持）。
    """
    _, _, fused = await hybrid_search_with_components(query, query_embedding, expand_bm25)
    return fused


def build_context_blocks(chunks: list[ChunkResult]) -> str:
    """検索チャンクをプロンプト用 context_blocks 形式に整形する。"""
    if not chunks:
        return "(コンテキストなし)"
    lines: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
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


def build_prompt(question: str, chunks: list[ChunkResult], history: list[dict]) -> str:
    """Ollama に渡す最終プロンプトを組み立てる。"""
    context_blocks = build_context_blocks(chunks)
    history_text = build_history_text(history)
    return (
        f"System:\n{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"History:\n{history_text}\n\n"
        f"Question:\n{question}\n"
    )


def build_sources_from_chunks(chunks: list[ChunkResult]) -> list[SourceItem]:
    """ChromaDB 検索結果メタデータから根拠リストを生成する（重複除去）。"""
    sources: list[SourceItem] = []
    seen: set = set()
    for chunk in chunks:
        meta = chunk["metadata"]
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
