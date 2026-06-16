<div align="center">

# GridMind
### Intelligence When the Grid Fails

A fully offline AI assistant for survival scenarios — no internet, no cloud, no compromise.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Powered-black)
![FAISS](https://img.shields.io/badge/FAISS-CPU_Optimized-orange)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![PWA](https://img.shields.io/badge/Frontend-PWA_Ready-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

## The Problem

When power grids fail, internet goes down. When internet goes down, your AI tools go with it.
GridMind is built for exactly that moment — a RAG-powered local AI that runs entirely on CPU, works offline, and answers survival-critical questions in minutes.

## What Makes It Different

| Feature | GridMind | Typical Chatbot |
|---|---|---|
| Internet required | No | Yes |
| Runs on CPU | Yes | Requires GPU or cloud |
| Memory | Stateful (Sliding Window) | Stateless or Cloud-dependent |
| Query Caching | Instant semantic retrieval | Redundant compute cycles |
| Custom knowledge base | Drop in any PDF | Fixed training data |
| Deployment target | Laptop, Raspberry Pi, Mobile (via LAN) | Server |

## Architecture

| Component | Model / Tool | Role |
|---|---|---|
| LLM | qwen2.5:3b via Ollama / llama.cpp | Response generation |
| Embeddings | nomic-embed-text | Semantic search |
| Vector Store | FAISS (cpu) | Fast retrieval |
| Backend | FastAPI | High-performance REST API |
| Frontend | Vanilla JS / CSS | Premium Brutalist PWA Interface |

## Core Features
- **Stateful Memory**: Maintains a sliding window of recent conversation turns to allow for natural follow-up questions without re-stating context.
- **Query Caching**: Built-in LRU cache for exact-match questions, bypassing the LLM entirely for instant responses to common survival queries.
- **Dynamic Personas**: Context-aware prompt injection based on urgency (e.g., Medical Triage vs Bushcraft Guide).
- **Markdown Streaming UI**: Real-time token streaming to a mobile-friendly frontend using Server-Sent Events (SSE).

## Optimizations for Constrained Devices

GridMind is aggressively optimized for hardware with limited RAM (4GB - 8GB) and no GPU.
- **Memory-Mapped Vectors**: FAISS index is loaded with `IO_FLAG_MMAP`.
- **Lazy Text Loading**: Document chunks and metadata are stripped of their raw text in memory.
- **Extreme Quantization**: `core/llm_engine.py` is explicitly tuned (`n_threads`, `use_mmap`) for low-vram targets using Q3_K_M/Q4_K_M GGUF models.
- **Query Embedding Cache**: Deduplicates embed calls for decomposed RAG queries, saving LLM compute.

## Knowledge Domains

Water purification, food sourcing, shelter building, first aid, navigation, equipment repair, emergency communication, disaster planning.

All source material belongs to respective authors and publishers.

## Setup

Requirements: Python 3.10+, [Ollama](https://ollama.com/)

```bash
# Clone and install
git clone https://github.com/A-Square8/GRIDMIND-Intelligence-When-the-Grid-Fails
cd GRIDMIND-Intelligence-When-the-Grid-Fails
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Pull models
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# Index knowledge base
python main.py index

# Launch the FastAPI Server
uvicorn interface.server:app --host 0.0.0.0 --port 8000
```
Then, open `http://localhost:8000` (or your laptop's local IP on your phone) to access the GridMind OS interface.

## Usage

```bash
python main.py index                          # Full index build
python main.py index --incremental            # Add new docs only
python main.py ask "how to purify water"      # Ask a question in terminal
python main.py retrieve "shelter" --top-k 8   # Test retrieval
```

**Expanding the knowledge base**

Drop any PDF or text file into `raw_docs/` and run:

```bash
python3 main.py index --incremental
```

Only new files are processed. The existing FAISS index is preserved.

## Contributing

Open to modifications, new knowledge domains, and improvements.
If you add something useful, a pull request is welcome.
