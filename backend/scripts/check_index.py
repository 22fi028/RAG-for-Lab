# [ROLE] ChromaDB の全チャンクを substring で検索し、MISS 質問の expected_keywords が物理的に存在するか診断するCLI
# [DEPS] core/config.py
# [CALLED_BY] (CLI) docker compose exec backend python scripts/check_index.py

import sys
from pathlib import Path

sys.path.insert(0, "/app")

import chromadb

from app.core.config import settings


KEYWORDS: list[str] = [
    "96kHz", "96 kHz", "96kHZ", "９６kHz",
    "Animal Pose", "animal pose", "Animal pose",
    "OKS", "ＯＫＳ",
    "差分ベクトル", "差分ベ クトル",
    "MAE", "R²", "R^2", "Ｒ²",
]
EXCERPT_LEN = 50
MAX_EXAMPLES = 3


def excerpt_around(text: str, needle: str, length: int = EXCERPT_LEN) -> str:
    """needle の前後を含めた抜粋を返す。改行は空白に置換する。"""
    flat = text.replace("\n", " ").replace("\r", " ")
    idx = flat.find(needle)
    if idx < 0:
        snippet = flat[:length]
    else:
        start = max(0, idx - length // 3)
        snippet = flat[start:start + length]
    snippet = snippet.strip()
    return snippet + ("..." if len(flat) > len(snippet) else "")


def fetch_all_chunks() -> list[tuple[str, str, dict]]:
    """ChromaDB から (id, content, metadata) を全件取得する。"""
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(settings.chroma_collection)
    results = collection.get(include=["documents", "metadatas"])
    ids = results.get("ids") or []
    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    return list(zip(ids, documents, [m or {} for m in metadatas]))


def find_keyword(chunks: list[tuple[str, str, dict]], keyword: str) -> list[tuple[str, str, dict]]:
    """キーワードを含むチャンクを返す（substring 完全一致、case-sensitive）。"""
    return [(cid, doc, meta) for cid, doc, meta in chunks if keyword in doc]


def format_doc_label(meta: dict) -> str:
    """メタデータから doc_id / title / page を読み取り、識別ラベルを作る。"""
    doc_id = meta.get("doc_id", "?")
    title = meta.get("title", "") or ""
    page = meta.get("page_num", 0) or 0
    if title:
        return f"doc_id={doc_id} title={title!r} p.{page}"
    return f"doc_id={doc_id} p.{page}"


def main() -> None:
    chunks = fetch_all_chunks()
    print(f"[check] total chunks in collection '{settings.chroma_collection}': {len(chunks)}")
    print()

    # 全キーワード検索結果を集計
    summary: list[tuple[str, int]] = []
    for kw in KEYWORDS:
        hits = find_keyword(chunks, kw)
        summary.append((kw, len(hits)))
        mark = "OK" if hits else "NG"
        label = f"[{kw}]"
        print(f"{label:<22} -> {len(hits)}件 [{mark}]")
        for cid, doc, meta in hits[:MAX_EXAMPLES]:
            print(f'  例: "{excerpt_around(doc, kw, EXCERPT_LEN)}"  {format_doc_label(meta)}')

    # サマリ
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    zero_keywords = [kw for kw, n in summary if n == 0]
    found_keywords = [(kw, n) for kw, n in summary if n > 0]
    print(f"total keywords: {len(KEYWORDS)}, found: {len(found_keywords)}, missing: {len(zero_keywords)}")
    if zero_keywords:
        print("0-hit keywords (likely missing or OCR-deformed):")
        for kw in zero_keywords:
            print(f"  - {kw}")
    if found_keywords:
        print("hit keywords:")
        for kw, n in found_keywords:
            print(f"  - {kw}: {n}件")


if __name__ == "__main__":
    main()
