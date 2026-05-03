# [ROLE] Recall@5 評価CLI: eval_set.jsonl の各質問に対しハイブリッド検索Top-5を行い、expected_keywords が全て含まれるチャンクの存在率を出力
# [DEPS] core/config.py, services/embedder.py, services/rag.py
# [CALLED_BY] (CLI) docker compose exec backend python scripts/eval_recall.py [--debug] [--expand]

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from app.services.embedder import embed_query
from app.services.rag import expand_query, hybrid_search


EVAL_SET_PATH = Path(__file__).parent / "eval_set.jsonl"
TOP_K = 5
EXCERPT_LEN = 60
DEBUG_EXCERPT_LEN = 100


def load_eval_set(path: Path) -> list[dict]:
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def excerpt(text: str, length: int = EXCERPT_LEN) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[:length] + "..."


def _strip_spaces(text: str) -> str:
    """半角・全角スペースを除去する。OCR/抽出で挿入される余計な空白の影響を避ける。"""
    return text.replace(" ", "").replace("　", "")


def chunk_contains_all_keywords(chunk_text: str, keywords: list[str]) -> bool:
    normalized_chunk = _strip_spaces(chunk_text)
    return all(_strip_spaces(kw) in normalized_chunk for kw in keywords)


async def _retrieve(query: str) -> list[dict]:
    embedding = embed_query(query)
    return await hybrid_search(query, embedding)


def evaluate(items: list[dict], debug: bool = False, expand: bool = False) -> tuple[int, int]:
    hits = 0
    total = 0

    for item in items:
        question = item["question"]
        keywords = item.get("expected_keywords", [])
        total += 1

        print(f"[eval] Q: {question}")

        query = question
        if expand:
            query = asyncio.run(expand_query(query))
            print(f"[eval]   expanded: {query}")

        chunks = asyncio.run(_retrieve(query))
        documents = [c.get("content", "") for c in chunks][:TOP_K]
        scores = [c.get("score", 0.0) for c in chunks][:TOP_K]

        if not documents:
            print("[eval]   → MISS (no results)")
            continue

        hit_index = -1
        for i, doc in enumerate(documents):
            if chunk_contains_all_keywords(doc, keywords):
                hit_index = i
                break

        if hit_index >= 0:
            hits += 1
            print(f'[eval]   → HIT  (chunk: "{excerpt(documents[hit_index])}") rrf_score={scores[hit_index]:.4f}')
        else:
            print(f'[eval]   → MISS (top chunk: "{excerpt(documents[0])}") rrf_score={scores[0]:.4f}')
            if debug:
                print("[eval]   Top-5 chunks:")
                for i, (doc, sc) in enumerate(zip(documents, scores), start=1):
                    print(f'[eval]     #{i} rrf_score={sc:.4f}: "{excerpt(doc, DEBUG_EXCERPT_LEN)}"')

    return hits, total


def main() -> None:
    parser = argparse.ArgumentParser(description="Recall@5 evaluation for RAG retrieval")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show all Top-5 chunks for MISS questions",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Enable query expansion via Ollama",
    )
    args = parser.parse_args()

    if not EVAL_SET_PATH.exists():
        print(f"eval set not found: {EVAL_SET_PATH}")
        sys.exit(1)

    items = load_eval_set(EVAL_SET_PATH)
    if not items:
        print("eval set is empty")
        sys.exit(1)

    hits, total = evaluate(items, debug=args.debug, expand=args.expand)
    recall = hits / total if total else 0.0
    print(f"Recall@{TOP_K}: {hits}/{total} = {recall:.2f}")


if __name__ == "__main__":
    main()
