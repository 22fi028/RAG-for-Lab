# RAG-for-Lab 開発ログ vol.4

**期間**: ハイブリッド検索の実装〜Recall@5ベースライン確定（0.33 → 0.58 → 0.92）
**対応要件定義書**: v1.5
**ブランチ**: dev → main にマージ済み

---

## 1. 実施内容サマリ

vol.3 でクエリ拡張が失敗（0.33 → 0.08）した後、方向転換して
ハイブリッド検索（BM25 + ベクトル + RRF）を導入。
さらに BM25 トークナイザの改善・データ整備・eval セット修正を経て
Recall@5 を **0.33 → 0.92** まで引き上げた。

---

## 2. Recall@5 の推移と各改善の原因

| # | タイミング | Recall@5 | 主な変更 |
|---|-----------|---------|---------|
| ① | ベースライン（vol.3） | **4/12 = 0.33** | ベクトル検索のみ |
| ② | クエリ拡張あり（vol.3） | 1/12 = 0.08 | 汎用語混入で悪化 → 不採用 |
| ③ | ハイブリッド検索導入後 | **7/12 = 0.58** | BM25 + ベクトル + RRF（whitespace split） |
| ④ | char N-gram 化 | 7/12 = 0.58 | tokenizer のみ変更（recall は変わらず） |
| ⑤ | 文書追加 + eval修正 | **11/12 = 0.92** | 動物姿勢推定論文等3本追加・`R²` → `R2` 修正 |
| ⑥ | 用語集チャンク削除後 | **11/12 = 0.92** | BM25 ノイズ源を排除（recall は変わらず） |

### 改善①: ハイブリッド検索（0.33 → 0.58）

#### 実装内容
- `backend/app/services/rag.py` に `search_bm25()` / `reciprocal_rank_fusion()` / `hybrid_search()` を追加
- BM25 索引はモジュール変数にメモリキャッシュし、文書追加・削除時は `invalidate_bm25_cache()` で破棄
- RRF 統合: `1 / (k + rank)` を両リストで合算（k=60）
- BM25 専用クエリ拡張 `expand_query_for_bm25()` を実装（ベクトル側は元クエリのまま）
- eval スクリプトの substring マッチを `_strip_spaces()` で正規化し OCR の余計な空白を吸収

#### 効果
- 0.33 → 0.58（+4問改善）
- ベクトル検索が苦手な「固有名詞・数値の完全一致」を BM25 がカバー

### 改善②: BM25 char N-gram 化（recall 変化なし）

#### 背景
日本語の whitespace split では「サンプリングレート」のような複合語が分割されず、
本文中の「サンプリング」「レート」と部分一致できなかった。

#### 実装内容
- `_tokenize()` を 2-gram + 3-gram の char N-gram 集合に変更
- 空文字・空白のみは空リストを返す
- パラメータは `settings.*` のまま不変

#### 効果
- Recall@5 は 0.58 で変化なし
- ただし BM25 単体スコアが大幅上昇（典型的なヒットチャンクで 20〜50 オーダー）
- **副作用**: `ML用語集`（1ドキュメントが10チャンク・専門用語数十個を含む）が
  N-gram 集合の語彙数で他チャンクを圧倒し、BM25 Top-5 を独占する現象が発生

### 改善③: 文書追加 + eval 修正（0.58 → 0.92）

#### 経緯
`check_index.py` を新規作成し、`expected_keywords` がインデックス内に
物理的に存在するか substring 検索で確認した結果:

| キーワード | 存在 | 原因 |
|--|--|--|
| `96kHz` / `96 kHz` | ◯（卒論発表 / 卒論フルペーパー） | retriever が拾えていないだけ |
| `Animal Pose` / `OKS` / `差分ベクトル` | × | **文書自体が未取り込み** |
| `R²` | ×、`R2` のみ存在 | OCR で上付き ² が ASCII `2` に潰れる |

#### 対応
1. 不足していた論文3本（動物姿勢推定・タスク編集・評価指標OKS）を追加取り込み（チャンク 675 → 689）
2. `eval_set.jsonl` の `R²` を `R2` に修正
3. `expected_keywords: ["96kHz"]` は `_strip_spaces()` 正規化により `96 kHz` と等価のため変更不要

#### 効果
- Recall@5: 0.58 → 0.92（+4問改善）
- HIT 化: 「回帰属性の評価指標（MAE/R2）」「動物姿勢推定のデータセット」「評価指標（OKS）」「タスク編集の手法名」

### 改善④: 用語集チャンク削除（recall 変化なし）

#### 経緯
char N-gram 化の副作用で `ML用語集` チャンクが BM25 Top-5 を支配していた。
`/admin` から削除したが、PostgreSQL レコードと ChromaDB チャンクが
データ不整合を起こしていたため、API `DELETE /api/documents/{id}` で再削除。

#### 効果
- BM25 Top-5 の構成は健全化（PSPNet・タスク編集論文等が入るように）
- ただし Recall@5 自体は 0.92 のまま（残る MISS は用語集と無関係）

---

## 3. 残課題

### 問題A残り: synonym ギャップ（中優先度）

**事象**: 「サンプリングレートは何か」が依然として MISS（11/12 → 12/12 にできない）

**根本原因**:
- 正解チャンク本文には「サンプリングレート」という語句がなく、
  値「アンビソニックマイクを4台使用 96kHz/24bit」だけが書かれている
- BM25 char N-gram は本文に語句がなければマッチできない
- ベクトル検索も「抽象概念名（サンプリングレート）」と
  「単位付き数値（96kHz）」の意味距離を埋めきれない

**次の対処候補**:
1. BM25 用 LLM クエリ拡張（既存 `expand_query_for_bm25()` の再評価）
2. HyDE（仮想回答を生成してベクトル検索）
3. クエリ前処理ルール（「〜は何か」→「〜 値 数値」等）

### 問題C（低優先度）: 根拠チップに無関係文書が混入
hybrid_search 導入後、再評価が必要。

### 問題D（低優先度）: 2列レイアウト論文のOCR読み順
vol.2 で部分対応済み。残るケースは後回し。

---

## 4. 追加した運用スクリプト

| ファイル | 用途 |
|--|--|
| `backend/scripts/eval_recall.py` | Recall@5 計測 CLI（`--debug` で BM25/Vector/RRF 個別 Top-5 表示） |
| `backend/scripts/eval_set.jsonl` | 評価セット 12 件 |
| `backend/scripts/check_index.py` | ChromaDB 全チャンクに対する substring 検索でキーワード存在確認 |

---

## 5. 設定値の現状

config.yaml（現在の値）

```
llm:
  model: "qwen3:8b"
  max_tokens: 1024
  temperature: 0.1

embedding:
  model: "intfloat/multilingual-e5-large"

rag:
  top_k: 5
  similarity_threshold: 0.5
  history_window: 5

chunking:
  chunk_size: 512
  chunk_overlap: 64
  min_chunk_length: 50

ocr:
  confidence_threshold: 0.8

pipeline:
  max_retry_attempts: 3
  base_delay_seconds: 1.0
```

ハイブリッド検索のハイパーパラメータ（rag.py 内の固定値）

| パラメータ | 値 | 場所 |
|--|--|--|
| RRF k | 60 | `reciprocal_rank_fusion()` 引数デフォルト |
| BM25 検索 top_k | `rag_top_k * 2` = 10 | `hybrid_search()` 内 |
| BM25 トークナイザ | char 2-gram + 3-gram | `_tokenize()` |

---

## 6. インデックス状態（dev → main マージ時点）

- ChromaDB コレクション `lab_rag`: **689 chunks / 12 documents**
- 内訳: 卒論フルペーパー / 卒論発表 / 卒論写真 / 軍神_要件定義 / 火災検出論文 /
  自動運転論文 / タスク編集論文 / および英語論文5本（HumanMAC, RoHM, DiffusionPoser, C2KD, Knowledge Distillation）

---

*作成日: 2026-05-04*
*次回: synonym ギャップ対策（BM25 クエリ拡張の再評価 / HyDE 検討）*
