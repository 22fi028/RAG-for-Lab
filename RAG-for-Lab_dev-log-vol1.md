# RAG-for-Lab 開発ログ vol.1

**期間**: 実データ検証フェーズ開始〜問題B完了  
**対応要件定義書**: v1.5  
**ブランチ**: dev（未マージ）

---

## 1. 実施内容

### 1-1. 実データ検証（PDF）

#### 検証環境
- 文書数: 8本（日本語2本・英語5本・OCR1本）
- similarity_threshold: 0.5 → 0.3 → 0.5（調整の経緯は後述）

#### 検証結果

| 条件 | Recall@5 |
|------|---------|
| 1文書・threshold=0.5 | 1.00 |
| 複数文書・threshold=0.5 | 0.60 |
| 複数文書・threshold=0.3 | 0.80 |

#### 判明した問題

| 問題 | 深刻度 | 状態 |
|------|--------|------|
| 短いクエリで「該当なし」になる | 中 | ✅ threshold調整で改善 |
| 文書数増加時に検索精度が低下する | 高 | ⏳ 未対処 |
| 根拠チップに無関係文書が混入する | 低 | ⏳ 保留 |
| 3Dメッシュツール名の誤答（1回のみ） | 低 | ⏳ 様子見 |

#### similarity_threshold の暫定値
現在 **0.5** で運用中。文書数・クエリの長さによって最適値が変わるため、
文書数が増えた段階で再調整が必要。

---

### 1-2. 形式別の精度評価

| 形式 | 精度 | 備考 |
|------|------|------|
| PDF | 文書数が少ないと高精度・増えると低下 | threshold調整で改善余地あり |
| PPTX | 高精度 | 問題なし |
| DOCX | 高精度 | 問題なし |
| 画像（OCR） | 部分的に認識・未認識箇所あり | 補正機能で対処済み |

---

### 1-3. 実装した機能（問題B: OCR可視化・補正）

#### コミット一覧

| コミットハッシュ | 内容 |
|----------------|------|
| `b3c4358` | feat: add ocr_results table and OCR detail API endpoint |
| `a69ad86` | feat: add OCR confidence badge to admin document table |
| `83407c7` | feat: add OCR detail viewer modal with bounding box overlay |
| `2c412f7` | fix: include avg_confidence in document list API to persist OCR badge |
| `(Step1)` | feat: add OCR text correction and reindex API |
| `(Step2)` | feat: add OCR text editor modal |
| `(Step3)` | feat: add reindex button for corrected OCR documents |

#### 実装内容の詳細

**DBの変更**

```
ocr_results テーブル（新規）
├── id
├── document_id    FK → documents.id / ON DELETE CASCADE
├── avg_confidence FLOAT
├── low_conf_count INTEGER
├── blocks         JSONB  ← OCR認識結果（座標・テキスト・信頼度）
└── corrected_text TEXT   ← 補正テキスト（NULLなら未補正）

documents テーブル（変更）
└── DocumentOut に avg_confidence・is_corrected を追加
```

**追加APIエンドポイント**

| メソッド | エンドポイント | 内容 |
|---------|--------------|------|
| GET | /api/documents/{id}/ocr | OCR詳細（blocks・信頼度）取得 |
| GET | /api/documents/{id}/image | 元画像ファイル取得 |
| GET | /api/documents/{id}/ocr/text | 補正テキスト取得（未補正ならblocks結合） |
| PUT | /api/documents/{id}/ocr/text | 補正テキスト保存 |
| POST | /api/documents/{id}/reindex | 再インデックス実行 |

**フロントエンドの変更**

- `/admin` DocumentTableに信頼度バッジ列を追加（🟢🟡🔴の3段階）
- 信頼度バッジクリックでOCR詳細ビューアモーダルを表示
  - 元画像にバウンディングボックスをオーバーレイ表示
  - ホバーでテキスト・信頼度のツールチップ表示
  - 右パネルにサマリー・ブロック一覧
- 「✏️ テキストを編集」ボタンでテキストエディタモーダルを表示
  - OCR認識テキストを編集・保存
  - 補正済みバッジ（✅）表示
- 補正済みOCR文書に「🔄 再インデックス」ボタンを表示
  - クリックで再インデックス実行
  - 処理中は「⏳ 処理中...」で無効化

**パイプラインの変更**

```python
# corrected_text があればそちらを優先（OCR再実行をスキップ）
if ocr_result and ocr_result.corrected_text:
    markdown_text = ocr_result.corrected_text
else:
    markdown_text = to_markdown_ocr(blocks)
```

---

## 2. 未解決の問題

### 問題A（高優先度）: 文書数増加時の検索精度低下

**現象**: 文書が8本程度でも「サンプリングレートは？」のような
短いクエリが `該当なし` になる場合がある。

**根本原因**: クエリが短すぎて多数のチャンクの中で埋もれる。
thresholdの調整は一時的な対処であり根本解決ではない。

**対処の方向性（要件定義書 Phase 4 相当）**:

| アプローチ | 効果 | 実装コスト |
|-----------|------|-----------|
| クエリ拡張 | 高 | 中 |
| ハイブリッド検索（BM25+ベクトル） | 高 | 高 |
| チャンクサイズ再調整 | 中 | 低 |

→ **次の会話で設計方針を決定する**

### 問題C（低優先度）: 根拠チップに無関係文書が混入

**現象**: 回答は正しいが、根拠チップに関係のない文書名が表示される。

**対処の方向性**: similarity_thresholdの最終調整で改善できる可能性あり。
問題Aの対処後に合わせて調整する。

### 問題D（検証待ち）: 2列レイアウト論文のOCR読み順

**現象**: 学術論文の2段組みレイアウトをOCRが横断して読む可能性がある。

**対処の方向性**: 実際の2列論文写真をアップロードして確認後に判断する。

---

## 3. 今後の方針

### 次の会話でやること

1. `dev` → `main` へのマージ
2. 問題A（文書数増加時の精度低下）の設計議論
   - クエリ拡張 vs ハイブリッド検索の選択
3. 問題Aの実装

### その後の課題

- similarity_thresholdの最終調整（問題C含む）
- 2列レイアウトOCRの検証（問題D）
- 文書数をさらに増やしてRecall@5を再計測

---

## 4. 設定値の現状

```yaml
# config.yaml（現在の値）
rag:
  similarity_threshold: 0.5  # 要調整
  top_k: 5
  history_window: 5

chunking:
  chunk_size: 512
  chunk_overlap: 64
  min_chunk_length: 50
```

---

*作成日: 2026-05-03*  
*次回: dev→mainマージ・問題A設計*
