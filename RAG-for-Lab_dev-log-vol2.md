# RAG-for-Lab 開発ログ vol.2

**期間**: 問題B残課題の修正・mainマージ  
**対応要件定義書**: v1.5  
**ブランチ**: dev → main マージ済み（`ee32c70..10a3720`）

---

## 1. 実施内容

### 1-1. 問題B残課題: OCRテキスト読み順の修正

#### 問題の概要

テキストエディタモーダルの初期テキストおよび再インデックス時のテキストが、
OCR認識ブロックの座標順ではなく格納順（不定）で結合されていた。

#### 原因の特定プロセス

| ステップ | 内容 |
|---------|------|
| 1 | `GET /api/documents/{id}/ocr/text` がAPIを正しく呼んでいることを確認 |
| 2 | コンテナ内で `grep` → `OCR_ROW_GAP_THRESHOLD` がコンテナに反映済みであることを確認 |
| 3 | `corrected_text` がNULLでないため `sort_blocks` を通らずに返していたことを発見 |
| 4 | DBで `corrected_text = NULL` にリセット後も変化なし → `sort_blocks` 自体をデバッグ |
| 5 | `sort_blocks` の出力は正しかったが、結合時に同一行を `\n` で区切っていたことが判明 |

#### 根本原因

`sort_blocks` はブロックを正しく読み順にソートしていたが、
テキスト結合時に全ブロックを `\n` で結合していた。
同一行のブロックをスペースで結合する処理が抜けていた。

#### 実装した修正

**① `sort_blocks` のソートロジック変更（`pipeline.py`）**

当初の固定bin幅方式（`BIN_SIZE=10` → `20`）では、同一行のyminが最大24pxばらつく
実データに対応できなかった。差分クラスタリング方式に変更。

```python
OCR_ROW_GAP_THRESHOLD = 15  # これ以上yminが離れたら別行とみなす

def sort_blocks(blocks: list[dict]) -> list[dict]:
    # yminで昇順ソート → 差分で行グループ割り当て → (row_id, xmin) でソート
```

**bboxのデータ形式（確認済み）**

`extract_ocr` がPaddleOCRの4頂点形式を `[xmin, ymin, xmax, ymax]` フラット配列に
正規化済み。`bbox[0]` = xmin、`bbox[1]` = ymin。

**② テキスト結合処理の修正（`documents.py` / `pipeline.py`）**

同一 `row_id` のブロックをスペースで結合し、行間のみ `\n` にする処理を追加。

```python
from itertools import groupby
lines = []
for _, group in groupby(blocks, key=lambda b: b["_row_id"]):
    line = " ".join(b.get("text", "") for b in group)
    lines.append(line)
text = "\n".join(lines)
```

修正箇所は2か所:
- `documents.py`: `get_document_ocr_text`（テキストエディタ表示時）
- `pipeline.py`: `to_markdown_ocr`（再インデックス時）

#### コミット一覧

| コミットハッシュ | 内容 |
|----------------|------|
| `1b39820` | fix: sort OCR blocks by reading order (ymin-bin → xmin) |
| `658b968` | fix: increase OCR_ROW_BIN_SIZE to 20 for better row grouping |
| `f57d2fa` | fix: replace bin-based OCR sort with gap-threshold clustering |
| `54a1e51` | fix: join same-row OCR blocks with space in ocr/text endpoint |
| `10a3720` | fix: apply same-row space joining to to_markdown_ocr in pipeline |

#### 修正結果

```
# 修正前
令和7年度
情報メディア学科
本業研究便覧集
足音に着目した人物解析データセット
の構築

# 修正後
令和7年度 情報メディア学科 本業研究便覧集
足音に着目した人物解析データセット の構築
```

RAG検索の動作確認:

> Q: 「足音データセットの撮影環境について教えて」  
> A: 「足音データセットの撮影環境は、反響を含む室内空間で行い、歩行領域は...
>    マイクは6.1m × 6.1m の正方形の四隅に対称配置し...」

概ね正確な回答が返るようになった。

---

## 2. 未解決の問題

### 問題A（高優先度）: 文書数増加時の検索精度低下

**現象**: 文書数8本でRecall@5 = 0.60（threshold=0.5）。
短いクエリが特に弱い。

**対処の方向性**: 次の会話で設計議論・実装。

### 問題D（低優先度）: 2列レイアウト論文のOCR読み順

**現象**: 2列組みレイアウトの論文で、左列と右列の同一行ブロックが
スペース結合されて混在する。

例: 「スマートホー センシング」（本来は左列「スマートホー」・右列「センシング」）

**対処の方向性**: 列検出ロジックが必要で実装コストが高いため後回し。

---

## 3. 設定値の現状

```yaml
# config.yaml（現在の値）
rag:
  similarity_threshold: 0.5  # 要調整（問題A対処後に再検討）
  top_k: 5
  history_window: 5

chunking:
  chunk_size: 512
  chunk_overlap: 64
  min_chunk_length: 50
```

```python
# pipeline.py（OCR固有定数）
OCR_ROW_GAP_THRESHOLD = 15  # px。隣接ブロック間のymin差がこれ以上なら別行
```

---

## 4. mainブランチの状態

`dev → main` マージ済み（`ee32c70..10a3720`、fast-forward、コンフリクトなし）。

---

*作成日: 2026-05-03*  
*次回: 問題A（文書数増加時の精度低下）設計議論・実装*
