# RAG-for-Lab

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Recall@5](https://img.shields.io/badge/Recall%405-0.92-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

> 研究室の過去知見（論文PDF・スライド・Word・紙の冊子）を自然言語で検索できる、
> ローカル完結・ゼロランニングコストの RAG システム。

## 概要

研究室には卒論PDF・発表スライド・Word文書・紙の冊子といった形で過去の知見が蓄積されているが、
それらは個人PCや共有フォルダに分散しており、検索性は実質的にゼロに近い。
B4・M1がテーマに関連する先行研究を把握するまでに数週間〜数ヶ月を要するのが現状で、
「すでに先輩が解決していた問題に再投資する」「過去の失敗を繰り返す」といったロスが恒常化していた。

本システムは、これらの分散知見を自然言語で検索・質問できる RAG として
研究室内に閉じた形で提供する。**ローカル完結・ゼロランニングコスト・フルOSS** を設計方針とし、
クラウドAPI料金や外部送信のリスクなしに、研究室の規模で常用できることを目指している。

## アーキテクチャ

```mermaid
graph LR
    A[PDF / PPTX\nDOCX / 画像] --> B[前処理パイプライン\nPyMuPDF / PaddleOCR\npython-pptx / python-docx]
    B --> C[(ChromaDB\nベクトルDB)]
    B --> D[(PostgreSQL\n会話履歴・文書管理)]
    C --> E[ハイブリッド検索\nBM25 + Vector + RRF]
    D --> E
    E --> F[Qwen3-8B\nOllama]
    F --> G[Web UI\nNext.js 14]
```

```
            ┌──────────────────────────┐
            │  ブラウザ (Next.js :3000) │
            └────────────┬─────────────┘
                         │ REST + SSE
                         ▼
            ┌──────────────────────────┐
            │     FastAPI (:8000)      │
            └─┬──────────┬───────────┬─┘
              │          │           │
    ┌─────────▼──┐  ┌────▼─────┐  ┌──▼──────────────┐
    │ PostgreSQL │  │ ChromaDB │  │ Ollama          │
    │  (:5432)   │  │ (file)   │  │ (host :11434)   │
    │ 会話履歴・  │  │ ベクトル  │  │ Qwen3-8B        │
    │ メタデータ  │  │ index    │  │                 │
    └────────────┘  └──────────┘  └─────────────────┘

埋め込みモデル: multilingual-e5-large（backend コンテナ内で実行）
```

## 技術スタック

| コンポーネント | ツール | 選定理由 |
|--------------|--------|---------|
| LLM | Qwen3-8B (Ollama) | 日本語対応・128kコンテキスト・VRAM 5.5GB・無料 |
| 埋め込み | multilingual-e5-large | 日本語対応・VRAM 0.6GB・ローカル実行可 |
| ベクトルDB | ChromaDB | ローカルファイル動作・メタデータ管理が容易 |
| キーワード検索 | BM25（rank-bm25） | 固有名詞・数値の完全一致に強い |
| 検索統合 | RRF（Reciprocal Rank Fusion） | BM25とベクトルの順位を正規化して統合 |
| バックエンド | FastAPI | SSEストリーミング・非同期処理が容易 |
| フロントエンド | Next.js 14 | App Router・TypeScript・Tailwind |
| DB | PostgreSQL | 会話履歴・文書メタデータの永続化 |
| OCR | PaddleOCR | 日本語対応・信頼度スコア出力・無料 |
| コンテナ | Docker Compose | 環境再現性・Ollama以外を一括管理 |

## 主な機能

- **マルチフォーマット取り込み**: PDF / PPTX / DOCX / 画像（OCR）をドラッグ＆ドロップでインデックス化
- **ハイブリッド検索**: BM25（キーワード）+ ベクトル検索 + RRF で統合。固有名詞・数値に強い
- **ストリーミングチャット**: SSE によるトークン単位の応答 + 根拠チップ（文書名・章・ページ）表示
- **根拠の明示**: LLM に生成させず ChromaDB メタデータから生成（ハルシネーション防止）
- **OCR可視化・補正UI**: バウンディングボックス付きで OCR 結果を確認、手動補正後に再インデックス
- **会話履歴の保存・復元**: PostgreSQL でセッション単位の対話履歴を永続化

## スクリーンショット

### チャット画面
![チャット画面](docs/images/chat_demo.png)

### 根拠チップ・文書ビューア
![文書ビューア](docs/images/doc_panel.png)

### 管理画面
![管理画面](docs/images/admin.png)

## 動作確認環境

| 項目 | 値 |
|------|-----|
| OS | Windows 11 / Ubuntu |
| GPU | NVIDIA RTX 3070（VRAM 8GB） |
| RAM | 32GB |
| Docker | 29.1.3 |
| Ollama | ホストPCで起動 |

## セットアップ

### 動作要件

| 項目 | 最小要件 | 推奨 |
|------|---------|------|
| GPU VRAM | 8GB以上 | 8GB（RTX 3070で動作確認済み） |
| RAM | 16GB以上 | 32GB |
| ストレージ | 20GB以上の空き | SSD推奨 |
| OS | Windows 11 / Ubuntu 22.04 | — |

> ⚠️ VRAM 8GB未満の環境ではQwen3-8B (Q4_K_M) が起動しません。
> CPUのみの環境では推論速度が大幅に低下します（1トークン/秒以下）。

---

### 初回起動の注意

初回起動時は以下のダウンロードが発生します（合計約6GB）。

| モデル | サイズ | ダウンロード先 |
|--------|--------|--------------|
| Qwen3-8B (Q4_K_M) | 約5.5GB | Ollama（`ollama pull qwen3:8b`） |
| multilingual-e5-large | 約0.6GB | HuggingFace（初回起動時に自動） |

ダウンロード完了まで環境により5〜15分かかります。
`backend` コンテナのログで進捗を確認できます。

```bash
docker compose logs -f backend
```

---

### 環境変数

`.env.example` をコピーしてそのまま動作します。
変更が必要な場合は以下を参考に編集してください。

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | OllamaのエンドポイントURL |
| `SIMILARITY_THRESHOLD` | `0.5` | 検索スコアの足切り閾値（0〜1） |
| `TOP_K` | `5` | 検索結果の上位件数 |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL接続文字列 |

---

### 評価の再現

付属の評価セット（`scripts/eval_set.jsonl`・12件）でRecall@5を再現できます。

```bash
# Recall@5 計測（期待値: 0.92 = 11/12）
docker compose exec backend python scripts/eval_recall.py

# MISSした質問のTop-5チャンクを確認
docker compose exec backend python scripts/eval_recall.py --debug

# ChromaDB内のキーワード存在確認
docker compose exec backend python scripts/check_index.py --keyword "96kHz"
```

---

### 前提

- Docker Desktop（Windows/Mac）または Docker Engine（Linux）
- Ollama インストール済み

### 手順

```bash
# 1. モデルの取得
ollama pull qwen3:8b

# 2. リポジトリのクローン
git clone https://github.com/22fi028/RAG-for-Lab.git
cd RAG-for-Lab

# 3. 環境変数の設定
cp .env.example .env
# .env はデフォルト値のままで動作する

# 4. 起動
## Windows
toggle.bat をダブルクリック（または start.bat）

## Linux / Mac
docker compose up -d
```

ブラウザで http://localhost:3000 を開く。

### Linux での追加設定

`host.docker.internal` が使えない環境では `docker-compose.yml` の backend サービスに以下を追加すること:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## 使い方

### 文書の追加

1. http://localhost:3000/admin を開く
2. PDF / PPTX / DOCX / 画像をドラッグ＆ドロップ
3. ステータスが `indexed` になれば検索可能

### 質問する

1. チャット画面で日本語で質問する
2. 回答の下に根拠チップ（文書名・章・ページ）が表示される
3. チップをクリックすると右パネルに該当箇所が表示される

### OCR文書の確認・補正

1. `/admin` の信頼度バッジをクリック → バウンディングボックス付きで OCR 結果を確認
2. 「テキストを編集」で手動補正
3. 「再インデックス」で反映

### 停止

```bash
# Windows
toggle.bat または stop.bat をダブルクリック

# Linux / Mac
docker compose down
```

## ディレクトリ構成

```
RAG-for-Lab/
├── backend/          # FastAPI
│   ├── app/
│   │   ├── core/     # 設定管理・リトライ
│   │   ├── models/   # SQLAlchemyモデル
│   │   ├── routers/  # APIエンドポイント
│   │   └── services/ # RAG・パイプライン・埋め込み
│   └── scripts/      # eval_recall.py・check_index.py
├── frontend/         # Next.js 14
├── data/             # ChromaDB・アップロードファイル（Git管理外）
├── config.yaml       # ハイパーパラメータ一元管理
└── docker-compose.yml
```

---

## 設計上の意思決定

### 根拠をLLMに生成させない
回答の根拠（文書名・章・ページ番号）はChromaDBの検索結果メタデータから
システムが直接生成する。LLMに生成させるとハルシネーション（存在しない
文書名の捏造）が発生するため採用しなかった。

**却下した方式：** プロンプトに「参照した文書名を末尾に列挙してください」と指示
→ 実在しない文書名・ページ番号を堂々と生成することを確認したため不採用。

---

### BM25のchar N-gramトークナイザ
日本語はスペース区切りでは複合語が分割されない。
whitespace splitから2-gram + 3-gramのchar N-gramに変更することで
「96kHz」「EasyMocap」のような固有名詞・数値の検索精度を改善した。

```python
# whitespace split（変更前）：「96kHz」→ ["96kHz"]（単語境界なし）
# char N-gram（変更後）：「96kHz」→ ["96", "6k", "kH", "Hz", "96k", "6kH", "kHz"]
```

---

### config.yaml → .envの2層設定管理
ハイパーパラメータ（RAGパラメータ・モデル名）はconfig.yamlで管理し、
DB接続・パスなど環境固有値は.envで管理。.envの同名変数がconfig.yamlを
上書きする構造。コンテナ再起動なしでパラメータ変更が反映される。
すべてのパラメータはsettings.*経由で参照し、ハードコード禁止。

```yaml
# config.yaml（ハイパーパラメータ）
retrieval:
  top_k: 5
  similarity_threshold: 0.5
  bm25_weight: 0.4
  vector_weight: 0.6
```

```bash
# .env（環境固有値・config.yamlを上書き）
SIMILARITY_THRESHOLD=0.3  # 本番環境では閾値を下げる場合
```

---

### 非同期インデックス化
アップロード後すぐ202 Acceptedを返し、BackgroundTasksで非同期実行。
フロントエンドが3秒ポーリングでステータス（pending→indexing→indexed/error）
を取得して表示更新。ユーザーが待機せずに他の操作を継続できる。
POST /documents/upload
→ 202 Accepted（即時返却）
→ BackgroundTasks: pipeline.run()
→ GET /documents/{id}/status（3秒ポーリング）
→ { "status": "indexed" }

---

### 埋め込みと検索でプレフィックスを使い分ける
multilingual-e5-largeの仕様に従い、格納時は `"passage: "`、
検索時は `"query: "` プレフィックスを付与。
混同するとベクトル空間がずれて精度が落ちる。

```python
# 格納時
embedding = model.encode("passage: " + chunk_text)

# 検索時
query_embedding = model.encode("query: " + user_query)
```

---

## 評価と改善

### Recall@5 の推移

評価セット12件に対する Retrieval 精度の改善推移。

![Recall@5改善推移](docs/images/recall_progress.png)

| # | 状態 | Recall@5 | 主な変更 |
|---|------|---------|---------|
| ① | ベースライン | 4/12 = 0.33 | ベクトル検索のみ |
| ② | クエリ拡張 | 1/12 = 0.08 | 汎用語混入で悪化 → 不採用 |
| ③ | ハイブリッド検索導入 | 7/12 = 0.58 | BM25 + ベクトル + RRF |
| ④ | BM25 char N-gram 化 | 7/12 = 0.58 | スコア改善・recall変化なし |
| ⑤ | 文書追加 + eval修正 | 11/12 = 0.92 | 未取り込み文書3本を追加 |

**目標値（Recall@5 ≥ 0.80）達成済み。**

### 失敗から学んだこと

クエリ拡張（0.33 → 0.08）が失敗した理由: LLM が「サンプリングレート」→「定義・とは・検索」のような汎用語を生成し、
埋め込みベクトルが正解チャンクの固有名詞（96kHz）から離れた。
「ベクトル検索の問題」ではなく「キーワード完全一致で解くべき問題」だったため、
BM25 の追加が正しいアプローチだった。

### 評価コマンド

```bash
# Recall@5 計測
docker compose exec backend python scripts/eval_recall.py

# デバッグモード（MISSした質問のTop-5を表示）
docker compose exec backend python scripts/eval_recall.py --debug

# ChromaDBのキーワード存在確認
docker compose exec backend python scripts/check_index.py
```

### 残課題

- **synonym ギャップ**: 「サンプリングレートは？」→ 本文には「96kHz」しかなく MISS。対策候補: HyDE（仮想回答でベクトル検索）
- **2列レイアウト論文の OCR 読み順**: 左右列の同一行が混在するケースが残存

## 今後の展望

- HyDE 導入: synonym ギャップの解消
- 学内サーバー移行: 複数人同時アクセス対応
- Kubernetes: `infra/k8s/` に参考マニフェストを配置予定
- Notion 連携: API 経由エクスポートの自動取り込み
- 認証機能: 学内メンバー限定アクセス
