# [ROLE] 埋め込みモデルのシングルトン管理（Phase 2 では起動ウォームアップ用のスタブ。Phase 4 で SentenceTransformer 実装に差し替える）
# [DEPS] core/config.py
# [CALLED_BY] services/pipeline.py, services/rag.py, main.py


class _StubEmbedder:
    """Phase 4 で SentenceTransformer に置き換えるまでの仮実装。"""

    def encode(self, texts):
        if isinstance(texts, str):
            return [0.0] * 1024
        return [[0.0] * 1024 for _ in texts]


_model = None


def get_embedder():
    global _model
    if _model is None:
        _model = _StubEmbedder()
    return _model


def embed_query(query: str) -> list:
    """Phase 4 で実装する。Phase 2 ではスタブ。"""
    return get_embedder().encode("query: " + query)
