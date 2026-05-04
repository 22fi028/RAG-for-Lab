# RAG-for-Lab 開発ログ vol.5

**期間**: ポートフォリオ仕上げ・企業評価対応
**対応要件定義書**: v1.5
**ブランチ**: dev → main マージ済み（ff8a6c2）

---

## 1. 実施内容

### 1-1. 企業目線（MLDS職）によるコード評価

Claude.aiによるコード全体レビューを実施。総評はB+（新卒・第二新卒採用において面接に進む水準）。

#### 高評価ポイント
- RAGパイプラインの設計理解（根拠をLLMに生成させずChromaDBメタデータから生成）
- クエリ拡張失敗（0.33→0.08）の原因分析と方向転換
- 評価基盤（eval_recall.py）を先に構築してから改善を進めた姿勢
- char N-gramトークナイザの採用判断（日本語whitespace分割の限界を理解）
- 非同期処理設計（BackgroundTasks + ポーリング）
- config.yaml → .env の2層設定管理

#### 指摘された改善点
| 優先度 | 問題 | 対応状況 |
|--------|------|---------|
| 高 | DocPanelの抜粋テキスト未実装 | ✅ 対応済み |
| 中 | sort_blocks/to_markdown_ocrの二重row_id計算 | ✅ 対応済み |
| 中 | チャンク型がsort dictで型安全性が低い | ✅ 対応済み |
| 低 | BM25マルチプロセス問題（将来課題） | ⏳ 未対応（現状ローカル単一プロセスで許容範囲） |

---

## 2. 実装した改善（3本）

### 2-1. DocPanel抜粋テキスト実装
**コミット**: 1ee9cd7 feat: implement chunk excerpt display in DocPanel

変更ファイル:
- config.yaml: rag.excerpt_max_length: 200 を追加
- backend/app/core/config.py: rag_excerpt_max_length を Settings に追加
- backend/app/routers/documents.py: GET /api/documents/chunk-excerpt を追加
  - title で ChromaDB を絞り、chapter/page_num は Python 側でフィルタ
  - 最初に一致したチャンクの先頭 settings.rag_excerpt_max_length 文字を返す
- frontend/src/components/DocPanel.tsx:
  - useEffect で source 変更時に fetch
  - ロード中「読み込み中...」、取得時は青ボックスに本文表示
  - 「実装予定」の文言を削除

### 2-2. sort_blocksリファクタリング
**コミット**: 0354b62 refactor: unify row_id ownership to sort_blocks

変更ファイル:
- backend/app/services/pipeline.py:
  - sort_blocks() が _row_id を付与したまま返すように変更（末尾のpop削除）
  - to_markdown_ocr() から自前の_row_id再計算ブロックを削除
  - sort_blocks() の _row_id を直接 groupby に渡し、末尾でクリーンアップ
- backend/app/routers/documents.py:
  - get_document_ocr_text() を同パターンで修正
  - 不要になった OCR_ROW_GAP_THRESHOLD のローカルインポートを削除

### 2-3. ChunkResult TypedDict導入
**コミット**: 415ca04 refactor: introduce ChunkResult TypedDict for type safety

変更ファイル:
- backend/app/services/rag.py:
  - ChunkResult / SourceItem TypedDict をファイル上部に定義
  - 主要関数のシグネチャを更新（search_chroma / search_bm25 / hybrid_search 等）
  - chunk.get("content", "") → chunk["content"] に置換
  - chunk.get("metadata") or {} → chunk["metadata"] に置換
  - metadata内部キーの .get() は optional なため維持

---

## 3. mainブランチの状態

マージコミット: ff8a6c2 merge: portfolio refactoring (DocPanel excerpt, sort_blocks, ChunkResult TypedDict)
origin/main に push 済み（cba2b47..ff8a6c2）

---

## 4. 未解決の問題

### 問題A残り: synonymギャップ（中優先度）
**事象**: 「サンプリングレートは何か」が依然 MISS（Recall 11/12 = 0.92）
**根本原因**: 正解チャンクに「サンプリングレート」という語がなく「96kHz/24bit」という値のみ存在
**次の対処候補**: HyDE（仮想回答生成→ベクトル検索）を優先検討
**現状の判断**: Recall@5 = 0.92 は要件定義書の目標値 0.80 を超過しており、
現段階での企業提示は可能と判断。synonymギャップ対策は次フェーズ。

### 問題C（低優先度）: 根拠チップに無関係文書が混入
ハイブリッド検索導入後に再評価が必要。

### 問題D（低優先度）: 2列レイアウト論文のOCR読み順
vol.2で部分対応済み。残るケースは後回し。

---

## 5. 設定値の現状

```yaml
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
  excerpt_max_length: 200

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

ハイブリッド検索のハイパーパラメータ（rag.py内固定値）

| パラメータ | 値 | 場所 |
|-----------|-----|------|
| RRF k | 60 | reciprocal_rank_fusion() 引数デフォルト |
| BM25検索 top_k | rag_top_k * 2 = 10 | hybrid_search() 内 |
| BM25トークナイザ | char 2-gram + 3-gram | _tokenize() |

---

## 6. インデックス状態（main マージ時点）

- ChromaDB コレクション lab_rag: 689 chunks / 12 documents

---

*作成日: 2026-05-04*
*次回: synonymギャップ対策（HyDE検討）または追加文書投入*
