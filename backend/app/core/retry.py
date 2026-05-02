# [ROLE] 指数バックオフ付きリトライデコレータ
# [DEPS] なし
# [CALLED_BY] services/rag.py, services/pipeline.py

import asyncio
from functools import wraps


def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """
    指数バックオフ付きリトライデコレータ。

    注意: async generator（yield を含む関数）には適用不可。
    stream_llm のような generator 関数には関数内ループで直接実装すること。

    バックオフ間隔: 1回目→1秒、2回目→2秒、3回目→4秒（base_delay × 2^attempt）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(base_delay * (2 ** attempt))
        return wrapper
    return decorator
