# 研究室特化型 RAG

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 概要

研究室には卒論PDF・発表スライド・Word文書・紙の冊子といった形で過去の知見が蓄積されているが、
それらは個人PCや共有フォルダに分散しており、検索性は実質的にゼロに近い。
B4・M1がテーマに関連する先行研究を把握するまでに数週間〜数ヶ月を要するのが現状で、
「すでに先輩が解決していた問題に再投資する」「過去の失敗を繰り返す」といったロスが恒常化していた。

本システムは、これらの分散知見を自然言語で検索・質問できる RAG（Retrieval-Augmented Generation）として
研究室内に閉じた形で提供する。**ローカル完結・ゼロランニングコスト・フルOSS** を設計方針とし、
クラウドAPI料金や外部送信のリスクなしに、研究室の規模で常用できることを目指している。

---

## 機能一覧

- **マルチフォーマット取り込み**: PDF / PPTX / DOCX / 画像（OCR）をドラッグ＆ドロップでインデックス化
- **ハイブリッド検索**: BM25（キーワード）+ ベクトル検索 + RRF（Reciprocal Rank Fusion）で統合
- **ストリーミングチャット**: SSE によるトークン単位の応答 + 根拠チップ（文書名・章・ページ）表示
- **OCR可視化・補正UI**: バウンディングボックス付きで OCR 結果を確認、手動補正後に再インデックス
- **会話履歴の保存・復元**: PostgreSQL でセッション単位の対話履歴を永続化
- **Recall@5 評価スクリプト**: `backend/scripts/eval_recall.py` で検索品質を定量的に測定可能

---

## アーキテクチャ

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

---

## 技術スタック

| コンポーネント | ツール | 選定理由 |
|---|---|---|
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

---

## 動作確認環境

| 項目 | 値 |
|---|---|
| OS | Windows 11 / Ubuntu |
| GPU | NVIDIA RTX 3070（VRAM 8GB） |
| RAM | 32GB |
| Docker | 29.1.3 |
| Ollama | ホストPCで起動 |

---

## セットアップ

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
chmod +x start.sh stop.sh toggle.sh
./start.sh
```

### Linux での追加設定

`host.docker.internal` が使えない環境では `docker-compose.yml` の
backend サービスに以下を追加すること:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

---

## 使い方

### 文書の追加

1. http://localhost:3000/admin を開く
2. PDF / PPTX / DOCX / 画像をドラッグ＆ドロップ
3. ステータスが `indexed` になれば検索可能

### 質問する

- チャット画面で日本語で質問する
- 回答の下に根拠チップ（文書名・章・ページ）が表示される
- チップをクリックすると右パネルに該当箇所が表示される

### OCR文書の確認・補正

1. `/admin` の信頼度バッジをクリック → バウンディングボックス付きでOCR結果を確認
2. 「テキストを編集」で手動補正
3. 「再インデックス」で反映

### 停止

```bash
# Windows
toggle.bat または stop.bat をダブルクリック

# Linux / Mac
./stop.sh
```

---

## 評価と改善

### Recall@5 の推移

| # | 状態 | Recall@5 | 主な変更 |
|---|---|---|---|
| ① | ベースライン | 4/12 = 0.33 | ベクトル検索のみ |
| ② | クエリ拡張 | 1/12 = 0.08 | 汎用語混入で悪化→不採用 |
| ③ | ハイブリッド検索導入 | 7/12 = 0.58 | BM25 + ベクトル + RRF |
| ④ | BM25 char N-gram 化 | 7/12 = 0.58 | スコア改善・recall変化なし |
| ⑤ | 文書追加 + eval修正 | 11/12 = 0.92 | 未取り込み文書3本を追加 |

### 失敗から学んだこと

クエリ拡張（0.33 → 0.08）が失敗した理由:
LLMが「サンプリングレート」→「定義・とは・検索」のような汎用語を生成し、
埋め込みベクトルが正解チャンクの固有名詞（96kHz）から離れた。
「ベクトル検索の問題」ではなく「キーワード完全一致で解くべき問題」だったため、
BM25 の追加が正しいアプローチだった。

### 残課題

- **synonym ギャップ**: 「サンプリングレートは？」→ 本文には「96kHz」しかなく MISS
  - 対策候補: HyDE（仮想回答でベクトル検索）
- **2列レイアウト論文のOCR読み順**: 左右列の同一行が混在するケースが残存

---

## 今後の展望

- **HyDE 導入**: synonym ギャップの解消
- **学内サーバー移行**: 複数人同時アクセス対応
- **Kubernetes**: `infra/k8s/` に参考マニフェストを配置済み（動作未検証）
- **Notion連携**: API経由エクスポートの自動取り込み
- **認証機能**: 学内メンバー限定アクセス

---

