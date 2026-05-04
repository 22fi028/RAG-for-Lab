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
from app.services.rag import hybrid_search_with_components


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


async def _retrieve_components(query: str, expand_bm25: bool) -> tuple[list[dict], list[dict], list[dict]]:
    embedding = embed_query(query)
    return await hybrid_search_with_components(query, embedding, expand_bm25=expand_bm25)


def _print_top5(label: str, chunks: list[dict], score_label: str, keywords: list[str]) -> None:
    """ラベル付きで Top-5 を表示し、各チャンクが expected_keywords を満たすかを併記する。"""
    print(f"[eval]   {label} Top-5:")
    if not chunks:
        print("[eval]     (no results)")
        return
    for i, c in enumerate(chunks[:TOP_K], start=1):
        doc = c.get("content", "")
        sc = c.get("score", 0.0)
        mark = "*HIT*" if chunk_contains_all_keywords(doc, keywords) else "     "
        print(f'[eval]     {mark} #{i} {score_label}={sc:.4f}: "{excerpt(doc, DEBUG_EXCERPT_LEN)}"')


def evaluate(items: list[dict], debug: bool = False, expand: bool = False) -> tuple[int, int]:
    hits = 0
    total = 0

    for item in items:
        question = item["question"]
        keywords = item.get("expected_keywords", [])
        total += 1

        print(f"[eval] Q: {question}")

        vector_results, bm25_results, fused = asyncio.run(_retrieve_components(question, expand_bm25=expand))
        documents = [c.get("content", "") for c in fused][:TOP_K]
        scores = [c.get("score", 0.0) for c in fused][:TOP_K]

        if not documents:
            print("[eval]   → MISS (no results)")
            if debug:
                print(f"[eval]   expected_keywords: {keywords}")
                _print_top5("BM25", bm25_results, "score", keywords)
                _print_top5("Vector", vector_results, "score", keywords)
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
                print(f"[eval]   expected_keywords: {keywords}")
                _print_top5("BM25", bm25_results, "score", keywords)
                _print_top5("Vector", vector_results, "score", keywords)
                _print_top5("RRF", fused, "rrf_score", keywords)

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
        help="Enable BM25-only query expansion via Ollama (vector query stays original)",
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
