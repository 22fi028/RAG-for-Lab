# 研究室特化型RAG — Claude Code 実装指示書

**対象**: Claude Code  
**バージョン**: v1.5  
**前提**: 要件定義書の内容がすべて確定済み  
**実装方針**: 既存コードは存在しない。0から実装すること。
             実装例が省略されている関数・コンポーネントは
             要件定義書の仕様に基づいて自分で実装すること。  
**作業ディレクトリ**: `C:\Projects\RAG-for-Lab`  
**GitHub リポジトリ**: `RAG-for-Lab`（private / main + dev ブランチ構成）

---

## 読む前に

この指示書は **上から順番に実行する**。セクションを飛ばさないこと。  
各セクションの末尾に「✅ 完了条件」を記載している。条件を満たしてから次へ進むこと。  
判断に迷ったら要件定義書 v1.4 を参照し、それでも不明な場合は作業を止めて確認を求めること。

---

## 環境情報

| 項目 | 値 |
|------|-----|
| OS | Windows 11 |
| GPU | NVIDIA RTX 3070 / VRAM 8GB |
| CPU | Intel Core i5-14400 |
| RAM | 32GB |
| Python | 3.11.9 |
| Docker | 29.1.3 |
| Docker Compose | v5.0.0 |
| CUDA | 13.1 |
| 作業ディレクトリ | `C:\Projects\RAG-for-Lab` |

---

## フェーズ一覧

| フェーズ | 内容 |
|---------|------|
| Phase 0 | 起動・停止スクリプト＆デスクトップショートカット作成 |
| Phase 1 | プロジェクト構成・Docker環境構築 |
| Phase 2 | バックエンド（FastAPI）実装 |
| Phase 3 | 前処理パイプライン実装 |
| Phase 4 | RAG検索・生成実装 |
| Phase 5 | フロントエンド（Next.js）実装 |
| Phase 6 | 統合テスト・動作確認 |

---

## Phase 0: 起動・停止スクリプト＆デスクトップショートカット作成

### 目的

デスクトップのショートカットを **1つだけ** 配置する。  
コンテナが停止中ならダブルクリックで起動、起動中ならダブルクリックで停止するトグル動作にする。

### 0-1. 起動スクリプトの作成

`C:\Projects\RAG-for-Lab\start.bat` を以下の内容で作成すること。

> **注意**: bat ファイルを UTF-8 で保存すると cmd.exe が Shift-JIS を期待するため日本語が文字化けしコマンドが誤動作する。メッセージは英語で記述すること。

```bat
@echo off
title RAG-for-Lab Starting...
echo [1/5] Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo [2/5] Waiting for Docker to be ready...
:wait_docker
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto wait_docker
)
echo Docker is ready.

echo [3/5] Starting Ollama...
start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 3 /nobreak >nul

echo [4/5] Starting RAG-for-Lab containers...
cd /d C:\Projects\RAG-for-Lab
docker compose up -d

echo [5/5] Opening browser...
timeout /t 15 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo  RAG-for-Lab is ready.
echo  Open http://localhost:3000
echo ========================================
pause
```

### 0-2. 停止スクリプトの作成

`C:\Projects\RAG-for-Lab\stop.bat` を以下の内容で作成すること。

```bat
@echo off
title RAG-for-Lab Stopping...
echo Stopping containers...
cd /d C:\Projects\RAG-for-Lab
docker compose down
echo.
echo RAG-for-Lab has been stopped.
pause
```

### 0-3. トグルスクリプトの作成

`C:\Projects\RAG-for-Lab\toggle.bat` を以下の内容で作成すること。  
`lab-rag-backend` コンテナの稼働状態を `docker ps` で確認し、起動中なら停止・停止中なら起動する。

```bat
@echo off
title RAG-for-Lab
cd /d C:\Projects\RAG-for-Lab

echo Checking container status...
docker ps --filter "name=lab-rag-backend" --filter "status=running" -q > "%TEMP%\rag_check.txt" 2>nul

set /p RUNNING=<"%TEMP%\rag_check.txt"
del "%TEMP%\rag_check.txt" >nul 2>&1

if "%RUNNING%"=="" (
    echo [STATUS] Stopped. Starting RAG-for-Lab...
    call start.bat
) else (
    echo [STATUS] Running. Stopping RAG-for-Lab...
    call stop.bat
)
```

### 0-4. デスクトップショートカットの作成

PowerShell で以下を実行してデスクトップにショートカットを **1つだけ** 作成すること。

```powershell
# 古いショートカットが残っていれば削除
Remove-Item "$Home\Desktop\RAG-for-Lab Start.lnk" -ErrorAction SilentlyContinue
Remove-Item "$Home\Desktop\RAG-for-Lab Stop.lnk" -ErrorAction SilentlyContinue

# トグル型ショートカットを1つ作成
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$Home\Desktop\RAG-for-Lab.lnk")
$Shortcut.TargetPath = "C:\Projects\RAG-for-Lab\toggle.bat"
$Shortcut.WorkingDirectory = "C:\Projects\RAG-for-Lab"
$Shortcut.Description = "Start or Stop RAG-for-Lab"
$Shortcut.Save()
```

### ✅ Phase 0 完了条件

- デスクトップに「RAG-for-Lab.lnk」が **1つだけ** 存在する
- コンテナ停止中にダブルクリック → 起動する
- コンテナ起動中にダブルクリック → 停止する

---

## Phase 1: プロジェクト構成・Docker環境構築

### 1-1. フォルダ・ファイル構成

`C:\Projects\RAG-for-Lab` を以下の構成にすること。存在しないフォルダ・ファイルはすべて作成すること。

```
RAG-for-Lab/
├── backend/
│   ├── app/
│   │   ├── __init__.py           （空ファイル）
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── __init__.py       （空ファイル）
│   │   │   ├── chat.py
│   │   │   ├── conversations.py
│   │   │   └── documents.py
│   │   ├── services/
│   │   │   ├── __init__.py       （空ファイル）
│   │   │   ├── rag.py
│   │   │   ├── pipeline.py
│   │   │   └── embedder.py
│   │   ├── models/
│   │   │   ├── __init__.py       （空ファイル）
│   │   │   └── db.py
│   │   └── core/
│   │       ├── __init__.py       （空ファイル）
│   │       ├── config.py
│   │       └── retry.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── （Phase 5 で Next.js プロジェクトを初期化する）
├── infra/
│   └── （将来の Kubernetes 用。現時点は空）
├── data/
│   ├── raw/
│   ├── processed/
│   └── chroma/
├── config.yaml                   （ハイパーパラメータ・モデル設定）
├── docker-compose.yml
├── .env                          （Git管理外）
├── .env.example                  （Git管理対象 — 値は空欄）
├── .gitignore
├── CLAUDE.md                     （Claude Code・Projects向け指示書）
├── README.md
├── LICENSE
├── start.bat
├── stop.bat
└── toggle.bat
```

### 1-2. config.yaml

ハイパーパラメータとモデル名をここで一元管理する。  
`.env` に同名変数がある場合は `.env` を優先する。  
`docker-compose.yml` の volume マウントにより、変更後のコンテナ再起動は不要。

```yaml
# [ROLE] RAG-for-Lab ハイパーパラメータ設定ファイル
# モデル名・RAGパラメータ・チャンク設定をここで一元管理する。
# .envに同名変数がある場合は.envを優先する。
# 変更後はDockerコンテナの再起動は不要（volumeマウントで即時反映）。

llm:
  model: "qwen3:8b"        # ollama pull qwen3:8b で取得するモデル名
  max_tokens: 1024          # 回答の最大トークン数
  temperature: 0.1          # 低いほどハルシネーション抑制

embedding:
  model: "intfloat/multilingual-e5-large"  # 日本語対応・VRAM約0.6GB

rag:
  top_k: 5                  # ChromaDB検索で取得するチャンク数
  similarity_threshold: 0.5 # これ未満のチャンクを除外
  history_window: 5         # 会話履歴の保持件数

chunking:
  chunk_size: 512            # トークン数上限（実データで調整する）
  chunk_overlap: 64          # チャンク間のオーバーラップ
  min_chunk_length: 50       # 50文字未満のチャンクを品質フィルタで破棄

ocr:
  confidence_threshold: 0.8  # これ未満の文書をレビューキューへ（暫定値）

pipeline:
  max_retry_attempts: 3      # インデックス化の最大リトライ回数
  base_delay_seconds: 1.0    # 指数バックオフの基準待機秒数
```

### 1-3. CLAUDE.md

プロジェクトルートに配置する。Claude Code および Claude.ai Projects が最初に読む指示ファイル。

````markdown
# CLAUDE.md — RAG-for-Lab

## プロジェクト概要
研究室の過去知見（論文PDF・スライド・Word）を自然言語で検索できるローカルRAGシステム。
ゼロランニングコスト・フルOSS・ローカル完結。

## 作業ディレクトリ
C:\Projects\RAG-for-Lab

## 現在のフェーズ
※ 作業開始時に必ず更新すること
Phase X: [作業中のフェーズ名]

## 技術スタック
- Backend : FastAPI + PostgreSQL + ChromaDB + Ollama (Qwen3-8B)
- Frontend : Next.js 14 (TypeScript / Tailwind CSS)
- Embedding: intfloat/multilingual-e5-large
- Infra    : Docker Compose (Windows 11 / RTX 3070)

## 設定ファイルの読み込み順序（重要）
1. config.yaml  → モデル名・RAGパラメータの基準値
2. .env         → DB接続・パスなど環境固有値（config.yamlを上書き）
3. app/core/config.py → 両方を統合してSettingsオブジェクトに注入

## ファイル先頭コメント規則（全ファイル必須）
各ファイルの1行目に以下を記述すること。
Claude Code がファイルの役割を即座に判断するために使用する。

Python:
# [ROLE] このファイルの役割（1行で）
# [DEPS] 依存するファイル名
# [CALLED_BY] このファイルを呼び出すファイル名

TypeScript:
// [ROLE] このファイルの役割（1行で）
// [DEPS] 依存するファイル名
// [CALLED_BY] このファイルを呼び出すファイル名

## ブランチ運用
- main : 動作確認済みコードのみ
- dev  : 開発作業はすべてここで行う
- 各Phaseの完了条件を満たしたら dev から main へマージする

## 実装フェーズ一覧
| Phase | 内容                        |
|-------|-----------------------------|
| 0     | 起動・停止スクリプト作成     |
| 1     | プロジェクト構成・Docker環境 |
| 2     | バックエンド（FastAPI）      |
| 3     | 前処理パイプライン           |
| 4     | RAG検索・生成               |
| 5     | フロントエンド（Next.js）    |
| 6     | 統合テスト                  |

## よく参照するファイル
- config.yaml              : ハイパーパラメータ一覧
- .env.example             : 環境変数テンプレート
- docker-compose.yml       : サービス構成
- backend/app/core/config.py : 設定の統合管理
````

### 1-4. .gitignore

```gitignore
# 環境変数（シークレットを含むため絶対にコミットしない）
.env

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# データ（論文データは Git 管理しない）
data/raw/
data/processed/
data/chroma/

# Node.js
node_modules/
.next/

# OS
.DS_Store
Thumbs.db
```

### 1-5. .env.example（Git管理対象）

```env
# Database
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=

# Ollama (running on host PC, outside Docker)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=

# ChromaDB
CHROMA_PATH=/data/chroma
CHROMA_COLLECTION=lab_rag

# RAG Parameters（未設定の場合は config.yaml の値を使用）
RAG_TOP_K=
RAG_SIMILARITY_THRESHOLD=
RAG_HISTORY_WINDOW=
RAG_MAX_TOKENS=
RAG_TEMPERATURE=

# Embedding Model（未設定の場合は config.yaml の値を使用）
EMBEDDING_MODEL=
```

### 1-6. .env（Git管理外 — 実際の設定値）

```env
POSTGRES_USER=labrag
POSTGRES_PASSWORD=labrag
POSTGRES_DB=labrag
DATABASE_URL=postgresql://labrag:labrag@db:5432/labrag

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:8b

CHROMA_PATH=/data/chroma
CHROMA_COLLECTION=lab_rag
```

> RAG パラメータ・モデル名は `config.yaml` で管理するため `.env` には記載しない。  
> `.env` で上書きしたい場合のみ追記すること。

### 1-7. docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    container_name: lab-rag-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/data
      - ./config.yaml:/app/config.yaml   # config.yaml をコンテナに即時反映
    env_file:
      - .env
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    depends_on:
      db:
        condition: service_healthy
    networks:
      - lab-rag-net
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: lab-rag-frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - lab-rag-net
    restart: unless-stopped

  db:
    image: postgres:16
    container_name: lab-rag-db
    ports:
      - "5432:5432"
    env_file:
      - .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U labrag"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - lab-rag-net
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  lab-rag-net:
    driver: bridge
```

### 1-8. backend/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--timeout-keep-alive", "120"]
```

### 1-9. backend/requirements.txt

バージョンは固定すること。

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
alembic==1.13.3
langchain==0.3.1
langchain-community==0.3.1
sentence-transformers==3.1.1
chromadb==0.5.15
PyMuPDF==1.24.10
paddlepaddle==2.6.2
paddleocr==2.8.1
python-pptx==1.0.2
python-docx==1.1.2
httpx==0.27.2
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.5.2
markdownify==0.13.1
pyyaml==6.0.2
```

> `pyyaml` を追加。`config.yaml` の読み込みに使用する。

### ✅ Phase 1 完了条件

- `docker compose build` がエラーなく完了する
- `docker compose up -d db` で db コンテナが `healthy` になる
- `docker compose ps` で db が `Up` 状態である

---

## Phase 2: バックエンド（FastAPI）実装

### 2-1. app/core/config.py

`config.yaml` を基準値として読み込み、`.env` の同名変数で上書きする。  
パラメータは必ずこの `settings` オブジェクト経由で参照すること（ハードコード禁止）。

```python
# [ROLE] 設定の統合管理: config.yaml（基準値）→ .env（上書き）の順で読み込む
# [DEPS] config.yaml, .env
# [CALLED_BY] main.py, services/rag.py, services/pipeline.py, services/embedder.py, routers/documents.py

import yaml
from pathlib import Path
from pydantic_settings import BaseSettings

def load_yaml_config() -> dict:
    yaml_path = Path("/app/config.yaml")
    if yaml_path.exists():
        with open(yaml_path) as f:
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

settings = Settings()
```

### 2-2. app/core/retry.py

```python
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
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(base_delay * (2 ** attempt))
        return wrapper
    return decorator
```

各エラーの最大試行回数:

| 対象 | max_attempts | 全失敗時の挙動 |
|------|-------------|--------------|
| Ollama 接続 | 3 | フロントへ type=error SSE で通知 |
| ChromaDB 検索 | 2 | 空リストで LLM 呼び出しを続行 |
| インデックス化パイプライン | 3 | status=error に更新・ログ記録 |

### 2-3. app/models/db.py

```python
# [ROLE] SQLAlchemy モデル定義（conversations / messages / documents テーブル）
# [DEPS] core/config.py
# [CALLED_BY] main.py, routers/chat.py, routers/conversations.py, routers/documents.py
```

SQLAlchemy のモデル定義。アプリ起動時に `Base.metadata.create_all(bind=engine)` でテーブルを自動作成すること。

**conversations テーブル**

| カラム | 型 | 備考 |
|--------|-----|------|
| id | UUID | PK |
| title | TEXT | nullable |
| created_at | TIMESTAMP | DEFAULT NOW() |

**messages テーブル**

| カラム | 型 | 備考 |
|--------|-----|------|
| id | UUID | PK |
| conversation_id | UUID | FK → conversations.id / ON DELETE CASCADE |
| role | TEXT | CHECK IN ('user', 'assistant') |
| content | TEXT | NOT NULL |
| sources | JSONB | nullable（根拠リスト） |
| created_at | TIMESTAMP | DEFAULT NOW() |

**documents テーブル**

| カラム | 型 | 備考 |
|--------|-----|------|
| id | UUID | PK |
| title | TEXT | nullable |
| author | TEXT | nullable |
| year | INTEGER | nullable |
| source_type | TEXT | `pdf` / `ocr` / `pptx` / `word` |
| file_path | TEXT | nullable |
| chunk_count | INTEGER | DEFAULT 0 |
| status | TEXT | DEFAULT 'pending'（pending / indexing / indexed / error） |
| error_message | TEXT | nullable（エラー詳細を記録） |
| created_at | TIMESTAMP | DEFAULT NOW() |

### 2-4. app/main.py

```python
# [ROLE] FastAPI アプリケーションのエントリーポイント・起動時の埋め込みモデルウォームアップ
# [DEPS] core/config.py, models/db.py, services/embedder.py, routers/*
# [CALLED_BY] uvicorn（Dockerfile CMD）

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, conversations, documents
from app.models.db import Base, engine
from app.services.embedder import get_embedder

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: 埋め込みモデルをロードしてウォームアップ
    # multilingual-e5-large のロードに 10〜30 秒かかるため
    # 起動完了前に質問が来るとエラーになるのを防ぐ
    print("Loading embedding model...")
    embedder = get_embedder()
    embedder.encode(["warmup"])
    print("Embedding model ready.")
    yield

app = FastAPI(title="研究室特化型RAG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(documents.router, prefix="/api", tags=["documents"])

@app.get("/health")
def health():
    try:
        get_embedder()
        embedding_status = "ready"
    except Exception:
        embedding_status = "loading"
    return {"status": "ok", "embedding_model": embedding_status}
```

### 2-5. app/routers/conversations.py

```python
# [ROLE] 会話セッションのCRUD APIエンドポイント
# [DEPS] models/db.py, core/config.py
# [CALLED_BY] main.py
```

```
GET    /api/conversations        → 会話一覧（created_at 降順）
GET    /api/conversations/{id}   → 特定会話のメッセージ一覧
POST   /api/conversations        → 新規会話作成
DELETE /api/conversations/{id}   → 会話削除（messages も CASCADE 削除）
```

レスポンス形式:

```json
[{"id": "uuid", "title": "...", "created_at": "2026-04-03T00:00:00"}]

{
  "id": "uuid", "title": "...",
  "messages": [
    {"id": "uuid", "role": "user", "content": "質問文", "sources": null, "created_at": "..."},
    {"id": "uuid", "role": "assistant", "content": "回答文",
     "sources": [{"title": "田中卒論", "chapter": "第3章", "page": 23}], "created_at": "..."}
  ]
}
```

### 2-6. app/routers/documents.py

```python
# [ROLE] 文書アップロード・一覧・削除・インデックス状況確認のAPIエンドポイント
# [DEPS] models/db.py, services/pipeline.py, core/config.py
# [CALLED_BY] main.py
```

```
POST   /api/documents              → ファイルアップロード（202 Accepted を即返す）
GET    /api/documents              → 文書一覧
DELETE /api/documents/{id}         → 文書削除（ChromaDB・ファイル・DB を連動削除）
GET    /api/documents/{id}/status  → インデックス化状況確認
```

受け付けるファイル拡張子: `.pdf` `.pptx` `.docx` `.png` `.jpg` `.jpeg`

**削除処理（3ステップ必ずこの順序で）**:

```python
@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Step 1: ChromaDB から削除（最大2回リトライ・指数バックオフ）
    for attempt in range(2):
        try:
            client = chromadb.PersistentClient(path=settings.chroma_path)
            collection = client.get_or_create_collection(settings.chroma_collection)
            results = collection.get(where={"doc_id": doc_id})
            if results["ids"]:
                collection.delete(ids=results["ids"])
            break
        except Exception as e:
            if attempt == 1:
                print(f"ChromaDB delete failed after 2 attempts: {e}")
            else:
                await asyncio.sleep(1.0)

    # Step 2: アップロードファイルを削除
    if doc.file_path and os.path.exists(doc.file_path):
        shutil.rmtree(os.path.dirname(doc.file_path), ignore_errors=True)

    # Step 3: PostgreSQL レコードを削除
    db.delete(doc)
    db.commit()
```

必要な import: `import os`, `import shutil`, `import asyncio`, `import chromadb`

### ✅ Phase 2 完了条件

- `http://localhost:8000/health` が `{"status": "ok", "embedding_model": "ready"}` を返す（最大30秒待つ）
- `http://localhost:8000/docs` で全エンドポイントが表示される
- `POST /api/conversations` で会話が作成できる
- `GET /api/conversations` が空のリストを返す

---

## Phase 3: 前処理パイプライン実装

### 3-1. app/services/pipeline.py のメインフロー

```python
# [ROLE] 文書インデックス化パイプライン（抽出→Markdown化→チャンキング→埋め込み→ChromaDB格納）
# [DEPS] core/config.py, core/retry.py, services/embedder.py
# [CALLED_BY] routers/documents.py

async def run_indexing_pipeline(doc_id: str) -> None:
    """
    status の遷移: pending → indexing → indexed / error
    エラー発生時は error_message に詳細を記録して status=error にすること。
    パイプライン全体のリトライは with_retry(max_attempts=settings.pipeline_max_retry) を使うこと。
    """
```

### 3-2. Step 1: テキスト抽出

**PDF（PyMuPDF）**
```python
import fitz

def extract_pdf(file_path: str) -> list[dict]:
    """戻り値: [{"page": 1, "text": "テキスト"}, ...]"""
    doc = fitz.open(file_path)
    return [
        {"page": i + 1, "text": page.get_text()}
        for i, page in enumerate(doc)
        if page.get_text().strip()
    ]
```

**PPTX（python-pptx）**
```python
def extract_pptx(file_path: str) -> list[dict]:
    """戻り値: [{"slide": 1, "text": "スライド本文\n話者ノート"}, ...]"""
```

**DOCX（python-docx）**
```python
def extract_docx(file_path: str) -> list[dict]:
    """戻り値: [{"page": 1, "text": "段落テキスト"}, ...]（ページは概算）"""
```

**画像（PaddleOCR）**

PaddleOCR はテキストブロック（行）ごとに 0.0〜1.0 の信頼度スコアを出力する。文書レベルのスコアは全ブロックの平均値で算出する。

```python
from paddleocr import PaddleOCR

_ocr = None

def get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="japan")
    return _ocr

def extract_ocr(file_path: str) -> dict:
    """
    信頼度スコアの算出:
      confidence = sum(score for _, score in ocr_results) / len(ocr_results)

    信頼度スコア < settings.ocr_confidence_threshold のブロックは除外する。

    戻り値:
    {
      "blocks": [{"page": 1, "text": "...", "confidence": 0.95}],
      "avg_confidence": 0.92,
      "low_conf_count": 3
    }
    """
```

> **注意**: OCR モデルと埋め込みモデルは起動時に一度だけロードしてグローバルにキャッシュすること。

### 3-3. Step 2: Markdown 構造化

```
# {見出し1}

## {見出し2}

{本文テキスト}
<!-- page: N -->
```

- PDF: ページ境界に `<!-- page: N -->` を挿入する
- PPTX: スライド境界に `<!-- slide: N -->` を挿入する

**自前パーサーの役割**

| 検出パターン | 変換例 |
|------------|--------|
| `第N章 〇〇` | `# 第1章 緒言` |
| `N.N 〇〇`（章番号） | `## 1.1 研究背景` |
| `N.N.N 〇〇`（節番号） | `### 1.1.1 実験条件` |

### 3-4. Step 3: メタデータ付与

```python
class ChunkMetadata(TypedDict):
    doc_id: str
    source_type: str        # pdf / ocr / pptx / word
    title: str
    author: str             # 不明な場合は空文字
    year: int               # 不明な場合は 0
    page_num: int           # 不明な場合は 0
    chapter: str            # 不明な場合は空文字
    section: str            # 不明な場合は空文字
```

### 3-5. Step 4: ハイブリッドチャンキング

chunk_size・chunk_overlap は必ず `settings` 経由で読むこと。

```python
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

HEADERS_TO_SPLIT = [
    ("#",   "chapter"),
    ("##",  "section"),
    ("###", "subsection"),
]

def chunk_markdown(markdown_text: str) -> list:
    md_splitter = MarkdownHeaderTextSplitter(HEADERS_TO_SPLIT)
    chunks = md_splitter.split_text(markdown_text)
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return char_splitter.split_documents(chunks)
```

### 3-6. Step 5: 品質フィルタリング

min_chunk_length は必ず `settings` 経由で読むこと。

**最低文字数フィルタ**

```python
final_chunks = [c for c in chunks if len(c.page_content) >= settings.min_chunk_length]
```

**重複チェック（同一文書内の完全一致を除去）**

```python
seen = set()
deduped = []
for chunk in final_chunks:
    key = (chunk.metadata["doc_id"], chunk.page_content.strip())
    if key not in seen:
        seen.add(key)
        deduped.append(chunk)
final_chunks = deduped
```

### 3-7. Step 6: 埋め込み生成

格納時は `"passage: "` プレフィックスを付与すること（検索時の `"query: "` と混同しないこと）。

```python
def embed_chunks(chunks: list) -> list[list[float]]:
    texts = ["passage: " + c.page_content for c in chunks]
    return get_embedder().encode(texts).tolist()
```

### 3-8. Step 7: ChromaDB 格納

```python
import chromadb
from uuid import uuid4

def store_to_chroma(chunks, embeddings, metadatas):
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(settings.chroma_collection)
    collection.add(
        embeddings=embeddings,
        documents=[c.page_content for c in chunks],
        metadatas=metadatas,
        ids=[str(uuid4()) for _ in chunks],
    )
```

### 3-9. パイプラインログ（9箇所）

```python
async def run_indexing_pipeline(doc_id: str) -> None:
    print(f"[pipeline] start doc_id={doc_id}")
    try:
        print(f"[pipeline] extracting file: {file_path}")
        print(f"[pipeline] markdown length: {len(markdown_text)} chars")
        print(f"[pipeline] chunking...")
        print(f"[pipeline] chunks before filter: {len(chunks)}")
        print(f"[pipeline] chunks after filter: {len(final_chunks)}")
        print(f"[pipeline] generating embeddings for {len(final_chunks)} chunks")
        print(f"[pipeline] storing to ChromaDB...")
        print(f"[pipeline] done. chunk_count={len(final_chunks)}")
    except Exception as e:
        print(f"[pipeline] error: {e}")
```

### ✅ Phase 3 完了条件

- `POST /api/documents` にサンプル PDF をアップロードすると 202 が返る
- `GET /api/documents/{id}/status` が `status=indexed` を返す
- `data/chroma/` にファイルが生成されている
- `chunk_count > 0` のレコードが PostgreSQL に存在する
- `docker compose logs -f backend` で9種類すべてのログが確認できる

---

## Phase 4: RAG 検索・生成実装

### 4-1. app/services/embedder.py

```python
# [ROLE] 埋め込みモデルのシングルトン管理・クエリ／パッセージの埋め込み生成
# [DEPS] core/config.py
# [CALLED_BY] services/pipeline.py, services/rag.py, main.py

from sentence_transformers import SentenceTransformer
from app.core.config import settings

_model = None

def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model

def embed_query(query: str) -> list[float]:
    """検索時は "query: " プレフィックスを付与すること"""
    return get_embedder().encode("query: " + query).tolist()
```

### 4-2. app/services/rag.py

```python
# [ROLE] ChromaDB検索・プロンプト組み立て・OllamaへのLLMストリーミング呼び出し
# [DEPS] core/config.py, core/retry.py, services/embedder.py
# [CALLED_BY] routers/chat.py
```

#### ChromaDB 検索

```python
def search_chroma(query_embedding: list[float]) -> list[dict]:
    """
    Top-k と similarity_threshold は settings 経由で読む。
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
            chunks = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                score = 1 - dist
                if score >= settings.rag_similarity_threshold:
                    chunks.append({"content": doc, "score": score, "metadata": meta})
            return chunks
        except Exception as e:
            if attempt == 1:
                print(f"ChromaDB search failed: {e}")
                return []
            await asyncio.sleep(1.0)
    return []
```

#### プロンプトテンプレート

```
System:
あなたは研究室の知識ベースアシスタントです。
与えられたコンテキストのみを根拠として回答してください。
コンテキストに情報がない場合は「該当する情報が見つかりませんでした」と答えてください。
回答は日本語で行ってください。
回答の末尾に【参照】を付ける必要はありません。根拠の表示はシステムが自動で行います。

Context:
{context_blocks}

History:
{history_text}

Question:
{question}
```

`context_blocks` の形式:
```
[1] {chunk.content}
出典: {chunk.metadata.title} / {chunk.metadata.chapter} / p.{chunk.metadata.page_num}
```

`history_text` の形式（直近 `settings.rag_history_window` 件）:
```
User: {message.content}
Assistant: {message.content}
```

#### Ollama ストリーミング呼び出し

> **注意**: `@with_retry` デコレータは async generator に適用不可。リトライは関数内ループで実装すること。

> **Qwen3 の thinking mode**: Qwen3 はデフォルトで thinking mode が ON のため RAG 用途では回答が冗長になる場合がある。system プロンプトに `/no_think` を追加するか、options に `"think": false` を渡すこと。

```python
import json, asyncio, httpx
from app.core.config import settings

async def stream_llm(prompt: str):
    max_attempts = settings.pipeline_max_retry
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
                        "options": {
                            "temperature": settings.rag_temperature,
                            "num_predict": settings.rag_max_tokens,
                        }
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            yield data.get("response", "")
                            if data.get("done"):
                                return
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(settings.pipeline_base_delay * (2 ** attempt))
```

#### 根拠の取得方式

LLM に【参照】を生成させず、ChromaDB の検索結果メタデータのみを使用すること（ハルシネーション防止）。

```python
def build_sources_from_chunks(chunks: list[dict]) -> list[dict]:
    sources, seen = [], set()
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("title", ""), meta.get("chapter", ""), meta.get("page_num", 0))
        if key not in seen:
            seen.add(key)
            sources.append({
                "title": meta.get("title", ""),
                "chapter": meta.get("chapter", ""),
                "page": meta.get("page_num", 0),
            })
    return sources
```

### 4-3. app/routers/chat.py

```python
# [ROLE] チャットAPIエンドポイント・SSEストリーミングレスポンスの送出
# [DEPS] services/rag.py, services/embedder.py, models/db.py, core/config.py
# [CALLED_BY] main.py
```

SSE フォーマット:
```
data: {"type": "token",  "content": "トークン文字列"}\n\n
data: {"type": "done",   "sources": [{"title": "...", "chapter": "...", "page": 23}]}\n\n
data: {"type": "error",  "message": "エラーメッセージ"}\n\n
```

> **注意**: ストリーミング内の DB 保存には `SessionLocal()` を直接使用すること（`next(get_db())` は不可）。

レスポンスヘッダーに `X-Accel-Buffering: no` を付与すること。

```python
async def generate_stream(req: ChatRequest, db: Session):
    try:
        # 履歴取得 → 埋め込み → 検索 → プロンプト組み立て
        full_response = ""
        async for token in stream_llm(prompt):
            full_response += token
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

        sources = build_sources_from_chunks(chunks)
        yield f"data: {json.dumps({'type': 'done', 'sources': sources}, ensure_ascii=False)}\n\n"

        session = SessionLocal()
        try:
            save_messages(session, req.conversation_id, req.question, full_response, sources)
            session.commit()
        finally:
            session.close()

    except httpx.ConnectError:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Ollama に接続できません。Ollama が起動しているか確認してください。'}, ensure_ascii=False)}\n\n"
    except httpx.TimeoutException:
        yield f"data: {json.dumps({'type': 'error', 'message': '回答生成がタイムアウトしました。もう一度試してください。'}, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'エラーが発生しました: {str(e)}'}, ensure_ascii=False)}\n\n"
```

### ✅ Phase 4 完了条件

- `POST /api/chat` で SSE トークンがストリーミングされる
- `type=done` イベントで根拠リストが返ってくる
- PostgreSQL に user・assistant メッセージが保存される

---

## Phase 5: フロントエンド（Next.js）実装

### 5-1. Next.js プロジェクトの初期化

> **注意**: ホスト PC に Node.js がない場合は `package.json` を手動作成し Docker コンテナ内で `npm install` を実行すること。

```bash
npx create-next-app@14 . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git
```

### 5-2. frontend/Dockerfile

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

### 5-3. コンポーネント構成

```
src/
├── app/
│   ├── page.tsx
│   └── admin/page.tsx
├── components/
│   ├── Header.tsx
│   ├── SideBar.tsx
│   ├── ChatArea.tsx
│   ├── DocPanel.tsx
│   └── admin/
│       ├── UploadArea.tsx
│       └── DocumentTable.tsx
└── hooks/
    ├── useChat.ts
    ├── useConversations.ts
    └── useDocuments.ts
```

各ファイルの先頭には `// [ROLE][DEPS][CALLED_BY]` コメントを必ず付けること。

### 5-4. メイン画面レイアウト仕様

```
┌──────────────────────────────────────────────────────┐
│  研究室特化型RAG  [Qwen3-8B]  [履歴Btn][文書Btn][管理Btn]  │ height: 48px
├──────────┬───────────────────────┬───────────────────┤
│ SideBar  │    ChatArea           │   DocPanel        │
│ w-[220px]│    flex-1             │   w-[300px]       │
│ toggle可 │                       │   toggle可        │
└──────────┴───────────────────────┴───────────────────┘
```

**Header**: タイトル「研究室特化型RAG」/ バッジ「Qwen3-8B」（緑）/ トグルボタン2つ / 管理画面ボタン

**SideBar**: 会話一覧 / 新規作成 / 削除ボタン / トグルで `w-0 opacity-0`（200ms）

**ChatArea**:
- ユーザー: 右寄せ・緑背景
- アシスタント: 左寄せ・グレー背景
- エラー（`isError: true`）: 赤背景
- 根拠チップ: `bg-blue-50 text-blue-800 rounded-full text-[11px]` / クリックで DocPanel に渡す
- ストリーミング中: トークン未着→バウンスドット / 到着後→カーソル `|` 点滅
- Enter 送信 / Shift+Enter 改行 / ストリーミング中は送信ボタン無効化

**DocPanel**: 根拠チップクリックで参照箇所（最大200文字）＋メタデータ表示 / トグルで `w-0 opacity-0`

**SSE 受信（useChat.ts）**:

```typescript
// [ROLE] SSE受信・メッセージ状態管理・ストリーミング制御のReact Hook
// [DEPS] なし（fetch APIのみ）
// [CALLED_BY] components/ChatArea.tsx

// type=token  → アシスタントメッセージに追記
// type=done   → sources をメッセージに紐付け・ストリーミング終了
// type=error  → isError: true で赤背景表示・ストリーミング終了
```

`Message` 型に `isError?: boolean` フィールドを追加すること。

### 5-5. 管理画面（/admin）仕様

- UploadArea: ドラッグ&ドロップ / `.pdf` `.pptx` `.docx` `.png` `.jpg` `.jpeg`
- DocumentTable: タイトル / 種別 / チャンク数 / ステータスバッジ / 登録日 / 削除ボタン
- ステータスバッジ: pending=グレー / indexing=黄（animate-pulse）/ indexed=緑 / error=赤
- ポーリング: pending・indexing は3秒ごとに status を取得、indexed・error でポーリング停止

### ✅ Phase 5 完了条件

- メイン画面が表示され、ストリーミング回答が返ってくる
- 根拠チップが表示され DocPanel に情報が出る
- 会話履歴の保存・復元ができる
- `/admin` でアップロード・インデックス化が完了する
- Ollama 停止時に赤背景エラーが表示される

---

## Phase 6: 統合テスト・動作確認

### 6-1. テスト手順

1. デスクトップの「RAG-for-Lab」ショートカットをダブルクリックして起動する
2. `docker compose ps` で全コンテナが `Up` であることを確認する
3. `GET /health` が `{"status": "ok", "embedding_model": "ready"}` を返すことを確認する（最大30秒）
4. `http://localhost:3000` で画面が表示されることを確認する
5. `/admin` でサンプル PDF をアップロードし `status=indexed` になるまで待つ（最大5分）
6. 文書に関する質問をしてストリーミング回答・根拠チップを確認する
7. 会話履歴の保存・復元を確認する
8. 文書削除後、削除した文書が根拠に出ないことを確認する
9. Ollama を停止した状態で質問し、赤背景エラーが出ることを確認する
10. ショートカットをダブルクリックで停止 → 再度ダブルクリックで復元できることを確認する

### 6-2. トラブルシューティング

| 症状 | 対処 |
|------|------|
| Ollama 接続失敗（502） | ホストで `ollama serve` を実行 |
| ChromaDB エラー | `icacls C:\Projects\RAG-for-Lab\data /grant Everyone:F /T` |
| PostgreSQL 接続失敗 | `docker compose logs db` で確認 |
| ストリーミング途切れ | Dockerfile CMD に `--timeout-keep-alive 120` があるか確認 |
| VRAM 不足 | 他アプリを閉じてから再起動 |
| OCR が動かない | コンテナログで確認（初回は自動ダウンロード） |
| 回答が冗長・長い | system プロンプトに `/no_think` を追加（Qwen3 thinking mode 対策） |
| config.yaml の変更が反映されない | docker-compose.yml の volume マウントを確認 |

---

## 付録: 完成形のディレクトリ構成

```
RAG-for-Lab/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── conversations.py
│   │   │   └── documents.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rag.py
│   │   │   ├── pipeline.py
│   │   │   └── embedder.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── db.py
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       └── retry.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   └── admin/page.tsx
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── SideBar.tsx
│   │   │   ├── ChatArea.tsx
│   │   │   ├── DocPanel.tsx
│   │   │   └── admin/
│   │   │       ├── UploadArea.tsx
│   │   │       └── DocumentTable.tsx
│   │   └── hooks/
│   │       ├── useChat.ts
│   │       ├── useConversations.ts
│   │       └── useDocuments.ts
│   ├── Dockerfile
│   └── package.json
├── infra/
├── data/
│   ├── raw/
│   ├── processed/
│   └── chroma/
├── config.yaml
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
├── LICENSE
├── start.bat
├── stop.bat
└── toggle.bat
```

---

*作成日: 2026-04-03 / 最終更新: 2026-05-01 / 対応要件定義書: v1.4*  
*変更履歴: v1.5 — Phase 0をトグル型ショートカット（1つ）に変更 / config.yaml追加 / CLAUDE.md追加 / ファイル先頭コメント規則追加*
