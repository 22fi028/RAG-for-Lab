# RAG-for-Lab CLAUDE.md

## プロジェクト概要
研究室の過去知見（論文PDF・スライド・Word）を自然言語で検索できるRAGシステム。
ローカル完結・ゼロランニングコスト。

## 技術スタック
- Backend: FastAPI + PostgreSQL + ChromaDB + Ollama(Qwen3-8B)
- Frontend: Next.js 14 (TypeScript, Tailwind)
- Embedding: multilingual-e5-large
- Infrastructure: Docker Compose

## 設定の読み込み順序（重要）
1. config.yaml → ハイパーパラメータ・モデル名の基準値
2. .env → DB接続・パスなどの環境固有値（config.yamlを上書き可能）
3. app/core/config.py → 両方を統合してSettingsに注入

## ファイル命名規則
- 各ファイル先頭に役割コメントを必ず記述（詳細は下記）

## 作業ディレクトリ
C:\Projects\RAG-for-Lab

## 現在の実装フェーズ
Phase X: [作業中のフェーズを都度更新]