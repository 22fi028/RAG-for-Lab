# [ROLE] 設定の統合管理: config.yaml（基準値）→ .env（上書き）の順で読み込む
# [DEPS] config.yaml, .env
# [CALLED_BY] main.py, services/rag.py, services/pipeline.py, services/embedder.py, routers/documents.py

import yaml
from pathlib import Path
from pydantic_settings import BaseSettings


def load_yaml_config() -> dict:
    yaml_path = Path("/app/config.yaml")
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = load_yaml_config()


class Settings(BaseSettings):
    # DB / パス系（.envのみ）
    database_url: str
    ollama_base_url: str
    chroma_path: str
    chroma_collection: str

    # チューニング系（config.yaml → .envで上書き可能）
    ollama_model: str = _yaml.get("llm", {}).get("model", "qwen3:8b")
    rag_top_k: int = _yaml.get("rag", {}).get("top_k", 5)
    rag_similarity_threshold: float = _yaml.get("rag", {}).get("similarity_threshold", 0.5)
    rag_history_window: int = _yaml.get("rag", {}).get("history_window", 5)
    rag_max_tokens: int = _yaml.get("llm", {}).get("max_tokens", 1024)
    rag_temperature: float = _yaml.get("llm", {}).get("temperature", 0.1)
    embedding_model: str = _yaml.get("embedding", {}).get("model", "intfloat/multilingual-e5-large")
    chunk_size: int = _yaml.get("chunking", {}).get("chunk_size", 512)
    chunk_overlap: int = _yaml.get("chunking", {}).get("chunk_overlap", 64)
    min_chunk_length: int = _yaml.get("chunking", {}).get("min_chunk_length", 50)
    ocr_confidence_threshold: float = _yaml.get("ocr", {}).get("confidence_threshold", 0.8)
    pipeline_max_retry: int = _yaml.get("pipeline", {}).get("max_retry_attempts", 3)
    pipeline_base_delay: float = _yaml.get("pipeline", {}).get("base_delay_seconds", 1.0)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
