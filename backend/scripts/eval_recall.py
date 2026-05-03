# [ROLE] Recall@5 評価CLI: eval_set.jsonl の各質問に対しTop-5検索を行い、expected_keywords が全て含まれるチャンクの存在率を出力
# [DEPS] core/config.py, services/embedder.py, services/rag.py
# [CALLED_BY] (CLI) docker compose exec backend python scripts/eval_recall.py [--debug] [--expand]

import argparse
import asyncio
import json
import sys
from pathlib import Path

import chromadb

sys.path.insert(0, "/app")

from app.core.config import settings
from app.services.embedder import embed_query
from app.services.rag import expand_query


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


def chunk_contains_all_keywords(chunk_text: str, keywords: list[str]) -> bool:
    return all(kw in chunk_text for kw in keywords)


def evaluate(items: list[dict], debug: bool = False, expand: bool = False) -> tuple[int, int]:
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(settings.chroma_collection)

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

        embedding = embed_query(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=TOP_K,
            include=["documents", "distances"],
        )
        documents = (results.get("documents") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

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
            score = 1 - distances[hit_index]
            print(f'[eval]   → HIT  (chunk: "{excerpt(documents[hit_index])}") score={score:.2f}')
        else:
            score = 1 - distances[0]
            print(f'[eval]   → MISS (top chunk: "{excerpt(documents[0])}") score={score:.2f}')
            if debug:
                print("[eval]   Top-5 chunks:")
                for i, (doc, dist) in enumerate(zip(documents, distances), start=1):
                    chunk_score = 1 - dist
                    print(f'[eval]     #{i} score={chunk_score:.2f}: "{excerpt(doc, DEBUG_EXCERPT_LEN)}"')

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
