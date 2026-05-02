# [ROLE] 埋め込みモデルのシングルトン管理・クエリ／パッセージの埋め込み生成
# [DEPS] core/config.py
# [CALLED_BY] services/pipeline.py, services/rag.py, main.py

from sentence_transformers import SentenceTransformer

from app.core.config import settings


_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    """埋め込みモデルのシングルトン取得。初回呼び出し時にロードする。"""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_query(query: str) -> list[float]:
    """検索時は 'query: ' プレフィックスを付与する（multilingual-e5-large の仕様）。"""
    return get_embedder().encode("query: " + query).tolist()
