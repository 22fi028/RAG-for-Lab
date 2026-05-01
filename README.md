# RAG-for-Lab

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A locally-hosted RAG (Retrieval-Augmented Generation) system designed for academic labs.  
Search across past theses, slides, and documents using natural language — fully offline, zero running cost.

---

## Features

- **Multi-format ingestion** — PDF, PPTX, DOCX, and scanned images (OCR)
- **Japanese-first** — Powered by `multilingual-e5-large` embeddings and `Qwen3-8B`
- **Source-grounded answers** — Every response cites the document, chapter, and page
- **Streaming responses** — Token-by-token output via SSE
- **Fully local** — No API keys, no cloud dependency, no running cost

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Qwen3-8B (Q4_K_M) via Ollama |
| Embedding | intfloat/multilingual-e5-large |
| Vector DB | ChromaDB |
| Backend | FastAPI + PostgreSQL |
| Frontend | Next.js 14 (TypeScript, Tailwind CSS) |
| Infrastructure | Docker Compose |

---

## Hardware Requirements

| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 3070 (VRAM 8GB) |
| RAM | 32GB recommended |
| OS | Windows 11 |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) with `qwen3:8b` pulled

```bash
ollama pull qwen3:8b
```

### Launch

Double-click `start.bat` on your desktop, or run:

```bash
docker compose up -d
```

Then open [http://localhost:3000](http://localhost:3000).

### Stop

```bash
docker compose down
```

---

## Configuration

All hyperparameters (model name, chunk size, RAG parameters) are managed in `config.yaml`.  
Environment-specific values (DB credentials, paths) are set in `.env` (see `.env.example`).

```yaml
# config.yaml — edit without restarting Docker
llm:
  model: "qwen3:8b"
  temperature: 0.1

rag:
  top_k: 5
  similarity_threshold: 0.5
```

---

## Project Structure

```
RAG-for-Lab/
├── backend/          # FastAPI application
├── frontend/         # Next.js application
├── data/             # Document storage (git-ignored)
├── config.yaml       # Hyperparameters
├── docker-compose.yml
├── start.bat         # One-click launcher
└── stop.bat
```

---

## Development

```bash
# Clone and switch to dev branch
git clone https://github.com/<your-id>/RAG-for-Lab.git
cd RAG-for-Lab
git checkout dev

# Copy environment template
cp .env.example .env
# Edit .env with your values

# Start services
docker compose up -d
```

---

## Roadmap

- [x] Project setup & Docker environment
- [ ] Preprocessing pipeline (PDF / OCR / PPTX / DOCX)
- [ ] RAG search & generation
- [ ] Web UI (chat + source panel)
- [ ] Evaluation & tuning

---

## License

MIT