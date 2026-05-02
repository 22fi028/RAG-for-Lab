# 研究室特化型RAG 要件定義書

**バージョン**: v1.5  
**作成日**: 2026-04-03  
**最終更新**: 2026-05-03  
**ステータス**: 確定（前処理パイプライン・技術選定）

---

## 目次

1. [背景・課題](#1-背景課題)
2. [システム概要](#2-システム概要)
3. [技術選定理由（各コンポーネント）](#3-技術選定理由各コンポーネント)
4. [前処理パイプライン詳細](#4-前処理パイプライン詳細)
5. [非機能要件](#5-非機能要件)
6. [今後の拡張方針](#6-今後の拡張方針)
7. [実装ロードマップ](#7-実装ロードマップ)

---

## 1. 背景・課題

### 研究室における知識継承の問題

研究室では毎年 B4・M1 の新メンバーが加わるが、過去の研究知見へのアクセスに大きなコストがかかっている。

| 課題 | 詳細 |
|------|------|
| **情報の断片化** | 紙の冊子・PDF・Word・スライドなど媒体が多種多様で情報が分散している |
| **検索コストの増大** | 媒体をまたいだ横断検索が困難で、過去研究の把握に膨大な時間を要する |
| **研究サイクルの遅延** | スタートアップが遅れ、「実験」に費やせる時間が減少する |

### 解決アプローチ

過去の分散した知見を統合し、**自然言語で対話・検索できるシステム**を構築することで、知見へのアクセスを高速化し研究サイクルを加速する。

---

## 2. システム概要

### プロダクト情報

| 項目 | 内容 |
|------|------|
| **システム名** | 研究室特化型RAG |
| **コンセプト** | 知見へのアクセスを高速にし、研究サイクルを加速する |
| **ターゲット** | 研究室所属の全学生（特に B4・M1） |
| **UI** | Web アプリ（ブラウザ操作） |
| **運用環境** | 個人 PC ローカル |

### ハードウェア環境

| パーツ | スペック |
|--------|----------|
| GPU | NVIDIA RTX 3070（VRAM 8GB） |
| CPU | Intel Core i5-14400 |
| RAM | 32GB |

### 対象データソース（優先度順）

1. **PDF**（卒論・修論）— テキスト埋め込み済みデジタル PDF
2. **紙の冊子**（OCR 処理が必要）
3. **スライド**（PPTX）
4. **Word 文書**

> **Notion などの API 経由エクスポートは現フェーズの対象外。** 検証コストが高いため今後の拡張方針（Phase 5）に移管する。

### システム構成（概略）

```
[データソース群]
    ↓
[前処理パイプライン]  ← 本ドキュメントの中心
    ↓
[Vector DB: ChromaDB]
    ↓
[LLM: Qwen3-8B (Q4_K_M) / Ollama]
    ↓
[Web UI: チャット + 根拠表示]
```

### 根拠の明示粒度

回答には必ず **文書名 + 該当章 / ページ番号** を付与する。  
ユーザーが元文書を確認できる信頼性を担保するため。

---

## 3. 技術選定理由（各コンポーネント）

### 基本方針

> **フルOSS・ゼロランニングコスト・ローカル運用**  
> 学生プロジェクトとして継続運用できるコスト構造を最優先とする。  
> 精度が要件を満たせない場合のみ有料サービスへの切り替えを検討する。

---

### 3-1. PDF 抽出 — `PyMuPDF (fitz)`

**選定理由**
- テキスト抽出と同時にページレイアウト・座標情報も取得できる
- テキスト埋め込み済み PDF であればそのまま高精度で抽出可能
- 処理速度が速く大量文書のバッチ処理に向いている
- 完全 OSS・無料

**代替候補と見送り理由**
- `pdfplumber`: レイアウト解析は優秀だが PyMuPDF より低速。**ただし表の抽出精度は pdfplumber が優れるため、論文中の表データの活用が必要になった段階で併用を検討する**
- `pdfminer`: 低レベル API で実装コストが高い

---

### 3-2. OCR エンジン — `PaddleOCR (ppstructure)`

**選定理由**
- 日本語に対応しており、文字認識精度が Tesseract より高い
- `ppstructure` モジュールでレイアウト解析（表・図・テキスト領域の分離）が可能
- 完全 OSS・無料でローカル実行できる
- 信頼度スコアを出力できるため、品質管理フローに組み込める

**代替候補と見送り理由**
- `Google Cloud Vision API`: 精度は最高水準だが有料。コスト方針に反する
- `Tesseract`: 無料・OSS だが日本語精度が PaddleOCR に劣る
- `Adobe Acrobat（手動）`: スケールしない。自動化不可

**将来の切り替え条件**  
PaddleOCR の精度が実用水準（信頼度 80% 以上のチャンクが全体の 90% 以上）を下回る場合、Google Cloud Vision API への移行を検討する。

---

### 3-3. PPTX / Word 抽出 — `python-pptx` / `python-docx`

**選定理由**
- スライドのテキスト・話者ノート・スライド番号を構造的に取得できる
- Word の段落・見出し階層をそのまま保持して抽出できる
- 完全 OSS・無料

---

### 3-4. Markdown 構造化 — `markdownify` + 自前パーサー

**選定理由**
- 全データソースを統一フォーマット（Markdown）に正規化することで、後続のチャンキング処理を単純化できる
- 見出し（`#` `##` `###`）・箇条書き・表を正規化しておくことで LangChain の `MarkdownHeaderSplitter` が正確に動作する

**自前パーサーの役割**

`markdownify` はHTMLやWord文書のような構造化されたソースには有効だが、PDFやOCRから抽出したプレーンテキストには見出し記号（`#`）が存在しない。自前パーサーは以下のパターンを検出して `#` を付与する処理を担う。

| 検出パターン | 変換例 |
|------------|--------|
| `第N章 〇〇` | `# 第1章 緒言` |
| `N.N 〇〇`（章番号） | `## 1.1 研究背景` |
| `N.N.N 〇〇`（節番号） | `### 1.1.1 実験条件` |

これにより `MarkdownHeaderSplitter` が正確に見出し単位でチャンクを分割できるようになる。

---

### 3-5. チャンキング — `LangChain`（ハイブリッド構成）

**選定理由**
- `MarkdownHeaderSplitter` により Markdown の見出し構造に沿った意味単位分割が可能
- `RecursiveCharacterSplitter` をフォールバックとして組み合わせることで、意味単位が長すぎる場合にも対応できる
- この組み合わせは RAG の標準的なベストプラクティスであり、実績が豊富

**チャンキング戦略（ハイブリッド）**

```
① 意味単位チャンク（優先）
   → Markdown の章・節・段落の区切りで分割
   → 見出しをチャンクに含め、文脈情報を保持する

② 固定長フォールバック
   → 意味単位チャンクが上限を超える場合に適用
   → 初期値: max 512 tokens / overlap 64 tokens
   → 実データで下限を探索し最適値を決定する
```

**チャンクサイズ探索方針**

1. サンプル論文 5 本でチャンク生成
2. 検索精度・文脈の切れ方を目視確認
3. 評価基準: 「1 チャンク = 1 つの問いに答えられる粒度」
4. 最小値を探索し、不要な過剰分割を排除する

---

### 3-6. 埋め込みモデル — `multilingual-e5-large`（sentence-transformers）

**選定理由**
- 日本語を含む多言語に対応しており、研究室の日本語文書に適している
- ローカル実行可能で API 呼び出しコストが発生しない
- RTX 3070 環境での VRAM 消費が約 0.6GB と軽量で、LLM との共存が可能
- sentence-transformers ライブラリで簡単に利用できる

**代替候補と見送り理由**
- `text-embedding-3-small`（OpenAI）: 精度は高いが有料。文書数が増えるとコスト増大

---

### 3-7. Vector DB — `ChromaDB`

**選定理由**
- ローカルファイルとして動作するため、サーバー構築が不要
- Python から直接扱えてセットアップコストがほぼゼロ
- ベクトルとメタデータ（文書名・章・ページ番号）をセットで管理できる
- 将来クラウド移行する際も Chroma の API 互換性が高い

**代替候補と見送り理由**
- `Pinecone`: 高機能だが有料・クラウド依存
- `pgvector`: PostgreSQL 拡張で堅牢だが、ローカル運用にはオーバースペック
- `FAISS`: 軽量だがメタデータ管理が別途必要で実装コストが高い

---

### 3-8. LLM — `Qwen3-8B (Q4_K_M量子化)` via Ollama

**選定理由**
- 日本語・多言語に対応しており、研究論文の専門用語を含む文書でも高い生成品質が期待できる
- 前世代と比較して同等 VRAM で性能が向上（thinking / non-thinking モード切り替え可能）
- RAG 用途では non-thinking モード（`/no_think`）を使用し、回答の冗長化を防ぐ
- 128k コンテキストウィンドウにより、複数チャンクを同時に参照できる
- Ollama 経由でローカル実行・完全無料

**量子化の選定方針**

| 量子化 | VRAM目安 | 精度 | 採用条件 |
|--------|---------|------|---------|
| Q4_K_M | 約 5.5GB | 標準 | **デフォルト採用** |
| Q5_K_M | 約 6.5GB | 高 | バッファ 1.5GB確保できる場合に検討 |

> Q5_K_M は精度が高いが、VRAM バッファが 1.5GB まで縮小する。他アプリとの共存時に不足する可能性があるため、実測で安定稼働を確認してから切り替えること。

**VRAM 配分計画**

| コンポーネント | VRAM 消費量 |
|---------------|-------------|
| Qwen3-8B | 約 5.5GB |
| multilingual-e5-large | 約 0.6GB |
| バッファ | 約 1.9GB |
| **合計** | **約 6.1GB / 8GB** |

> 埋め込み生成と LLM 推論は直列処理とし、VRAM の同時使用量を抑制する。

**セットアップコマンド**

```bash
ollama pull qwen3:8b
ollama run  qwen3:8b
```

**Phase 2 への切り替え条件**  
チャンク設計が安定し、トークン消費が最小化できた段階で `GPT-4o-mini` への移行を検討する。

---

## 4. 前処理パイプライン詳細

### 全体フロー

```
[データソース]
    ↓
[Step 1] ソース別テキスト抽出
    ↓
[Step 2] OCR 処理（紙の冊子のみ）
    ↓
[Step 3] Markdown 構造化（全ソース共通）
    ↓
[Step 4] メタデータ付与（全ソース共通）
    ↓
[Step 5] ハイブリッドチャンキング
    ↓
[Step 6] 品質チェック & フィルタリング
    ↓
[Step 7] 埋め込み生成
    ↓
[Step 8] Vector DB 格納（ChromaDB）
```

### Step 1: ソース別テキスト抽出

| データソース | ツール | 取得内容 |
|-------------|--------|---------|
| デジタル PDF | PyMuPDF | テキスト・ページ番号・レイアウト |
| PPTX | python-pptx | スライドテキスト・話者ノート・スライド番号 |
| Word | python-docx | 段落・見出し階層 |

### Step 2: OCR 処理（紙の冊子のみ）

**推奨スキャン条件**: 解像度 300dpi 以上、グレースケールまたはカラー

**OCR 信頼度スコアについて**

PaddleOCR はテキストブロック（行）ごとに 0.0〜1.0 の信頼度スコアを出力する。このスコアは OCR モデルの認識確信度を表し、文字の鮮明さ・フォントの認識しやすさ・ノイズ量などに基づいてモデルが内部的に算出する。

**文書レベルの信頼度スコアの集計方法**

```python
# 全ブロックの信頼度スコアの平均値を文書スコアとして使用
confidence = sum(score for _, score in ocr_results) / len(ocr_results)
```

**OCR 品質管理フロー**

```
PaddleOCR 実行（ブロックごとに信頼度スコアを出力）
    ↓
文書全体の平均信頼度スコアを算出
    ↓
閾値判定（デフォルト: 80%）
    ├─ スコア ≥ 80% → 自動で次工程へ
    └─ スコア < 80% → レビューキューへ
                           ↓
                       開発者が目視確認
                           ↓
                       修正して再投入 or スキップ判断
```

> 閾値 80% は暫定値。実データでの検証後に調整する。

### Step 3: Markdown 構造化

全ソースを以下の統一フォーマットへ正規化する。

```markdown
# 第1章 緒言

## 1.1 研究背景

本研究は...

## 1.2 研究目的

...
```

### Step 4: メタデータ付与

各チャンクに以下のメタデータを付与する。

```json
{
  "source_type": "pdf | ocr | pptx | word",
  "doc_id": "UUID",
  "title": "◯◯に関する研究",
  "author": "山田 太郎",
  "year": 2023,
  "page_num": 12,
  "chapter": "第3章",
  "section": "3.2 実験方法"
}
```

### Step 5: ハイブリッドチャンキング

```python
# 実装イメージ
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Step A: 意味単位分割（優先）
headers_to_split_on = [
    ("#",  "chapter"),
    ("##", "section"),
    ("###","subsection"),
]
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
chunks = md_splitter.split_text(markdown_text)

# Step B: 固定長フォールバック
char_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,      # 実データで探索
    chunk_overlap=64,
)
final_chunks = char_splitter.split_documents(chunks)
```

### Step 6: 品質チェック & フィルタリング

| チェック項目 | 条件 | 処理 |
|-------------|------|------|
| 最低文字数 | 50 文字未満 | チャンクを破棄 |
| OCR 信頼度 | スコア < 80% | 人手レビューキューへ |
| 重複チェック | 同一内容の重複 | 重複を除去 |

**最低文字数（50文字）の根拠**

チャンキング後に生成される断片的なテキスト（ページ番号のみ・図表のキャプション1行など）は意味のある情報を持たず、検索ノイズになる。50文字はおおよそ「1文以上の情報」が含まれる最低ラインとして設定した暫定値。実データ検証で調整する。

```python
# 実装イメージ
final_chunks = [c for c in chunks if len(c.page_content) >= 50]
```

**重複チェックの具体的な方法**

同一 `doc_id` 内で `page_content` が完全一致するチャンクを除去する。PDF のヘッダー・フッター（ページ番号、大学名、著者名など）が全ページに繰り返し出現する場合に有効。

```python
# 実装イメージ（同一文書内の完全一致重複を除去）
seen = set()
deduped = []
for chunk in final_chunks:
    key = (chunk.metadata["doc_id"], chunk.page_content.strip())
    if key not in seen:
        seen.add(key)
        deduped.append(chunk)
```

> 現時点では「完全一致」のみを除去。類似文（意味的重複）の除去は精度向上フェーズで検討する。

### Step 7: 埋め込み生成

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-large")
embeddings = model.encode(
    ["passage: " + chunk.page_content for chunk in final_chunks]
)
```

> `multilingual-e5-large` は `query:` / `passage:` プレフィックスが必要。  
> 格納時は `passage:` 、検索時は `query:` を付与する。

### Step 8: Vector DB 格納

```python
import chromadb
from uuid import uuid4

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("gunsin")

collection.add(
    embeddings=embeddings,
    documents=[c.page_content for c in final_chunks],
    metadatas=[c.metadata for c in final_chunks],
    ids=[str(uuid4()) for _ in final_chunks],
)
```

### Step 9: パイプラインログ

各ステップに `print(f"[pipeline] ...")` でログを出力すること。`docker compose logs -f backend` で進行状況をリアルタイムに追跡できる。

| ステップ | ログ出力 |
|---------|---------|
| 開始 | `[pipeline] start doc_id=...` |
| テキスト抽出 | `[pipeline] extracting file: ...` |
| Markdown 変換 | `[pipeline] markdown length: ... chars` |
| チャンキング開始 | `[pipeline] chunking...` |
| フィルタ前 | `[pipeline] chunks before filter: ...` |
| フィルタ後 | `[pipeline] chunks after filter: ...` |
| 埋め込み生成 | `[pipeline] generating embeddings for ... chunks` |
| ChromaDB 格納 | `[pipeline] storing to ChromaDB...` |
| 完了 | `[pipeline] done. chunk_count=...` |
| エラー | `[pipeline] error: ...` |

---

## 5. 非機能要件

| 項目 | 要件 | 備考 |
|------|------|------|
| **応答時間** | 質問から回答まで 5 秒以内 | ローカル LLM のため変動あり |
| **セキュリティ** | ローカル運用・学内データ外部送信なし | Ollama はオフライン動作 |
| **可用性** | 個人 PC 稼働時のみ（ローカル動作） | 精度が保証され次第、学内サーバーへの常時稼働を実装予定（Phase 5） |
| **運用負荷** | 文書追加時のみパイプライン実行 | バッチ処理で対応 |
| **データ保護** | 論文データはローカルのみ保持 | クラウドアップロード禁止 |

---

## 6. 今後の拡張方針

### Phase 1（現在）: 実データ検証 ― ベースライン確立

- 実際の卒論・修論データを投入して動作確認
- チャンクサイズ（暫定 512tok）を実データで探索・最適化
- 検索精度（Recall@k）・回答品質のベースラインを計測
- **弱点・課題を特定する**: 検索ヒット率の問題か、LLM 生成の問題かを切り分ける

**評価指標: Recall@k について**

| 項目 | 内容 |
|------|------|
| **指標** | Recall@k |
| **定義** | 正解チャンクのうち Top-k 検索結果に含まれていた割合 |
| **採用理由** | 研究室用途では「情報の取りこぼし」が最大のリスク。Hit Rate は1件でもヒットすれば1.0になるため取りこぼしを検出できず、MRR は順位を重視するため網羅性の評価に不向き。Recall@k は正解チャンクを何件回収できたかを直接測定できるため本システムに最適 |
| **目標値** | Recall@5 ≥ 0.80（実データ検証後に調整） |
| **測定方法** | 既知の答えを持つ質問セットを手動作成し、正解チャンクが Top-k に含まれるかを確認する |

### Phase 2: LLM モデル交換

- Qwen3-8B（現行）から最新ローカル LLM へ切り替えて比較検証
  - 候補: Gemma 4（Ollama 対応済み）/ PrismML Bonsai（1-bit・VRAM 1.15GB・研究段階）
- **制約**: RTX 3070 / VRAM 8GB のため、モデル選定時は VRAM 消費量を必ず確認
- 比較は同一論文・同一クエリセットで行い、RAGAS 指標で定量評価する

### Phase 3: 実データ検証 ― モデル交換後の評価

- Phase 2 で交換したモデルでの検索精度・回答品質を再計測
- Phase 1 のベースラインと比較し、改善量を定量化
- 残存する弱点・課題を整理する

### Phase 4: 精度向上の工夫

Phase 1・3 の検証結果をもとに、弱点に応じた改善策を選択する。

| 弱点の種類 | 改善アプローチ |
|-----------|-------------|
| 検索がそもそもヒットしない | エージェント検索の導入 / ハイブリッド検索（BM25 + ベクトル）/ チャンク再設計 |
| ヒットしているが回答が悪い | プロンプト改善 / LLM 再選定 / コンテキスト量の調整 |
| 特定の文書形式で精度が低い | OCR 精度向上 / 構造化方法の改善 |
| 回答が遅い | モデルの量子化レベル調整 / キャッシュ導入 |

> **ベクトル検索の廃止・変更も視野に入れる**: 検索ヒット率が根本的に低い場合は、ベクトル検索をやめてエージェント検索（LLM が自律的に複数クエリを発行して検索）に切り替えることも検討する。

### Phase 5: 共有・運用

- 学内サーバーへの移行（複数人が同時アクセス可能な構成）
- Kubernetes による本番環境構築（ポートフォリオ兼用）
- 認証機能の追加（学内メンバー限定アクセス）
- 文書追加の自動化（フォルダ監視による自動インデックス）
- **Notion 連携の追加**（API 経由エクスポート対応 — 現フェーズでは対象外）

---

## 7. 実装ロードマップ

### マイルストーン

| フェーズ | 内容 | 目安 |
|---------|------|------|
| M1 | 環境構築・PoC | 1〜2週間 |
| M2 | 前処理パイプライン実装 | 2〜3週間 |
| M3 | RAG 検索・生成の実装 | 1〜2週間 |
| M4 | Web UI 実装 | 1〜2週間 |
| M5 | 評価・チューニング | 継続 |

### タスク一覧

#### M1: 環境構築・PoC

- [ ] Python 仮想環境の構築（venv / conda）
- [ ] Ollama インストール・`qwen3:8b` のダウンロード
- [ ] ChromaDB・LangChain・sentence-transformers のインストール
- [ ] PaddleOCR のインストール・動作確認
- [ ] サンプル PDF 1 本でエンドツーエンドの動作確認

#### M2: 前処理パイプライン実装

- [ ] PyMuPDF による PDF テキスト抽出モジュール
- [ ] PaddleOCR による OCR モジュール + 信頼度チェック
- [ ] python-pptx による PPTX 抽出モジュール
- [ ] python-docx による Word 抽出モジュール
- [ ] Markdown 構造化・正規化モジュール
- [ ] メタデータ付与モジュール
- [ ] ハイブリッドチャンキングモジュール
- [ ] 品質チェック・フィルタリングモジュール
- [ ] ChromaDB への格納モジュール
- [ ] チャンクサイズ探索実験（サンプル論文 5 本）

#### M3: RAG 検索・生成の実装

- [ ] クエリの埋め込み生成（`query:` プレフィックス付与）
- [ ] ChromaDB での Top-k 検索
- [ ] プロンプトテンプレートの設計（根拠明示を含む）
- [ ] Ollama API 経由での LLM 回答生成
- [ ] 根拠（文書名・章・ページ）の抽出・フォーマット

#### M4: Web UI 実装

- [ ] チャット画面（質問入力・回答表示）
- [ ] 根拠表示パネル（文書名・章・ページ）
- [ ] 文書アップロード・インデックス管理 UI
- [ ] 会話履歴の保持

#### M5: 評価・チューニング

- [ ] 検索精度の評価（Recall@k）
- [ ] 回答品質の主観評価
- [ ] チャンクサイズの最終調整
- [ ] OCR 品質の統計確認

---

*最終更新: 2026-04-19*

---

## 8. UI設計

### 画面構成

#### メイン画面（3カラム構成・各パネルトグル可能）

```
┌──────────────────────────────────────────────────────┐
│  研究室特化型RAG  [Qwen3-8B]    [履歴ボタン][文書ボタン][設定] │  ← ヘッダー (48px)
├──────────┬───────────────────────┬───────────────────┤
│          │                       │                   │
│  会話    │    チャットエリア      │   文書ビューア    │
│  履歴    │                       │                   │
│  220px   │       flex: 1         │     300px         │
│ （トグル）│                       │    （トグル）     │
└──────────┴───────────────────────┴───────────────────┘
```

#### パネルトグル仕様

- ヘッダー右上に「履歴」「文書ビューア」の個別トグルボタンを配置
- 非表示にするとチャットエリアが `flex: 1` で自動拡張
- 入力欄下部に現在の表示状態をインジケーター表示（● 表示中 / ○ 非表示）
- アクティブなボタンは背景色で状態を区別

#### 左カラム: 会話履歴（220px）

- 新しい会話ボタン
- 会話一覧（タイトル + 日付）
- アクティブな会話をハイライト（左ボーダー + 背景色で強調）
- トグルボタンで非表示にできる（幅 0 + opacity 0 でアニメーション）

#### 中央カラム: チャットエリア（flex: 1）

- メッセージ一覧（ユーザー右寄せ / アシスタント左寄せ）
- アシスタントの回答直下に根拠チップを表示
  - 例: `田中卒論 p.23 第3章` `鈴木卒論 p.41 第4章`
  - チップをクリック → 右パネルの文書ビューアに該当箇所を表示
- 入力エリア（テキストエリア + 送信ボタン）

#### 右カラム: 文書ビューア（300px）

- 参照箇所のハイライト表示（抜粋テキスト + 出典ラベル）
- 文書メタデータ（著者・年度・種別・ページ）
- ページプレビュー（該当行をブルーでハイライト）
- トグルボタンで非表示にできる（幅 0 + opacity 0 でアニメーション）

#### 管理画面

| 機能 | 内容 |
|------|------|
| 文書アップロード | ドラッグ&ドロップ / ファイル選択 |
| インデックス状況 | 文書一覧・チャンク数・ステータス表示 |
| 文書削除・管理 | 文書単位での削除・再インデックス |

---

## 9. 検索・生成フロー（RAGパイプライン）

### コンテキスト（会話履歴）戦略

#### Phase 1: 直近N件方式（採用）

```python
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(k=5)  # 直近5件
```

**採用理由**: 実装がシンプルで追加LLM呼び出しが不要。Qwen3-8Bは128kコンテキストを持つため、N=5〜10件程度では超過しない。

#### Phase 2: 要約方式（将来検討）

```python
from langchain.memory import ConversationSummaryMemory

memory = ConversationSummaryMemory(llm=llm)  # 1行差し替えで移行可能
```

**切り替え条件**: 会話が長期化しコンテキスト不足による回答品質の低下を確認した時点で移行する。

---

### クエリ処理フロー

```
[1] ユーザー質問入力（Next.js）
    ↓
[2] POST /api/chat（FastAPI）
    ↓
[3] 会話履歴取得（PostgreSQL — 直近5件 / ConversationBufferWindowMemory）
    ↓
[4] クエリ埋め込み生成（multilingual-e5-large / "query: " プレフィックス付与）
    ↓
[5] ベクトル検索（ChromaDB — Top-k=5 / 類似度スコア + メタデータ取得）
    ↓
[6] スコアフィルタリング（類似度 < 0.5 のチャンクを除外）
    ↓
[7] プロンプト組み立て（LangChain）
    ↓
[8] LLM 回答生成（Ollama — Qwen3-8B / ストリーミング）
    ↓
[9] レスポンス整形（回答 + 根拠リスト / PostgreSQL に保存）
    ※ 根拠は LLM の出力からではなく ChromaDB の検索結果メタデータから生成する
    （LLM によるハルシネーション防止）
    ↓
[10] UI 表示（チャット + 根拠チップ + 文書ビューア）
```

### プロンプトテンプレート（初期設計）

```
System:
あなたは研究室の知識ベースアシスタントです。
与えられたコンテキストのみを根拠として回答してください。
コンテキストに情報がない場合は「該当する情報が見つかりませんでした」と答えてください。

Context:
{チャンク1} [出典: {文書名} {章} p.{ページ}]
{チャンク2} [出典: {文書名} {章} p.{ページ}]
...

History:
{直近の会話履歴}

Question:
{ユーザーの質問}

回答の末尾に【参照】を付ける必要はありません。根拠の表示はシステムが自動で行います。
```

### パラメータ設定（初期値）

| パラメータ | 値 | 備考 |
|-----------|-----|------|
| Top-k | 5 | 実データで調整 |
| 類似度閾値 | 0.5 | 低品質チャンク除外 |
| 会話履歴 | 直近5件（Phase 1） | トークン節約のため。Phase 2 で要約方式を検討 |
| max_tokens | 1024 | 回答の最大長 |
| temperature | 0.1 | ハルシネーション抑制 |

> **根拠の生成方式について**: LLM に【参照】を生成させる方式は採用しない。LLM が存在しない文書名を捏造するリスクがあるため、ChromaDB の検索結果チャンクのメタデータをそのまま根拠リストとして使用する。

---

### ストリーミング実装方針

Ollama のネイティブストリーミング API を直接使用し、FastAPI から SSE（Server-Sent Events）でフロントエンドへトークンを逐次送信する。

```python
# FastAPI 側 — SSE でストリーミング
from fastapi.responses import StreamingResponse
import httpx

async def stream_ollama(prompt: str):
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": "qwen3:8b",
                  "prompt": prompt, "stream": True}) as r:
            async for chunk in r.aiter_text():
                yield f"data: {chunk}

"

@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(stream_ollama(req.prompt),
                             media_type="text/event-stream")
```

```typescript
// Next.js 側 — SSE を受信してリアルタイム表示
const res = await fetch("/api/chat", { method: "POST", body: ... });
const reader = res.body!.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  setMessage(prev => prev + new TextDecoder().decode(value));
}
```

---

### 文書インデックス化：非同期処理設計

アップロード受付と実際のインデックス化処理を分離する。FastAPI の `BackgroundTasks` を使用し、アップロード完了後すぐにレスポンスを返しながらバックグラウンドでインデックス化を進める。

```
[1] POST /api/documents（ファイル受信）
    ↓ 即座に 202 Accepted を返す
[2] BackgroundTasks でインデックス化開始
    ├─ 前処理パイプライン実行
    ├─ ChromaDB に格納
    └─ PostgreSQL の status を更新
        pending → indexing → indexed / error
[3] GET /api/documents/{id}/status でポーリング
    → フロントエンドが状態を定期取得して表示更新
```

```python
@router.post("/documents", status_code=202)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    doc = create_document_record(db, file.filename)  # status: pending
    background_tasks.add_task(run_indexing_pipeline, doc.id, file)
    return {"id": doc.id, "status": "pending"}
```

---

### エラーハンドリング方針

指数バックオフ付きリトライを基本とする。

全エラーに指数バックオフ（base_delay=1.0秒）を適用する。接続系・IO系エラーは時間をおくことで回復する可能性があるため。

| エラー種別 | リトライ | バックオフ | 処理 |
|-----------|---------|-----------|------|
| Ollama 接続失敗 | 最大3回 | 指数バックオフ | 全失敗時はエラーメッセージをフロントへ返す |
| ChromaDB 検索失敗 | 最大2回 | 指数バックオフ | 全失敗時は空リストで LLM 呼び出しを続行 |
| インデックス化失敗 | 最大3回 | 指数バックオフ | 全失敗時は status を `error` に更新・ログ記録 |
| OCR 信頼度不足 | リトライなし | なし | レビューキューへ追加（精度問題はリトライで解決しないため） |

> バックオフ間隔: 1回目 → 1秒待機、2回目 → 2秒待機、3回目 → 4秒待機（base_delay × 2^attempt）

```python
import asyncio
from functools import wraps

def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
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

### APIエンドポイント設計

| メソッド | エンドポイント | 内容 |
|---------|--------------|------|
| POST | /api/chat | 質問送信・回答取得（SSEストリーミング） |
| GET | /api/conversations | 会話一覧取得 |
| GET | /api/conversations/{id} | 会話履歴取得 |
| DELETE | /api/conversations/{id} | 会話削除 |
| POST | /api/documents | 文書アップロード |
| GET | /api/documents | 文書一覧取得 |
| DELETE | /api/documents/{id} | 文書削除 |
| GET | /api/documents/{id}/status | インデックス状況確認 |

### PostgreSQL テーブル設計（概略）

```sql
-- 会話セッション
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- メッセージ
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT,
    sources JSONB,   -- 根拠リスト [{doc, chapter, page}]
    created_at TIMESTAMP DEFAULT NOW()
);

-- 文書管理
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    author TEXT,
    year INTEGER,
    source_type TEXT,
    file_path TEXT,
    chunk_count INTEGER,
    status TEXT DEFAULT 'pending',  -- pending / indexed / error
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

*最終更新: 2026-04-19*
