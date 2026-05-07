<div align="center">

# GridMind
### Intelligence When the Grid Fails

A fully offline AI assistant for survival scenarios — no internet, no cloud, no compromise.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Powered-black)
![FAISS](https://img.shields.io/badge/FAISS-CPU_Optimized-orange)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)


</div>



## The Problem

When power grids fail, internet goes down. When internet goes down, your AI tools go with it.
GridMind is built for exactly that moment — a RAG-powered local AI that runs entirely on CPU,
works offline, and answers survival-critical questions in minutes.


<!--## Demo

> Record a 30-second terminal session using asciinema or a screen recorder and drop the GIF here.-->



## What Makes It Different

| Feature | GridMind | Typical Chatbot |
|---|---|---|
| Internet required | No | Yes |
| Runs on CPU | Yes | Requires GPU or cloud |
| Custom knowledge base | Drop in any PDF | Fixed training data |
| Incremental indexing | SHA-256 diff, no rebuild | Full rebuild |
| Deployment target | Laptop, Raspberry Pi | Server |



## Architecture

![architecture](https://github.com/user-attachments/assets/12fd8f1d-28af-4778-9d96-3cd6e246713e)


| Component | Model / Tool | Role |
|---|---|---|
| LLM | qwen2.5:3b via Ollama | Response generation |
| Embeddings | nomic-embed-text | Semantic search |
| Vector Store | FAISS (cpu) | Fast retrieval |
| UI | Streamlit | Dashboard |



## Knowledge Domains

Water purification, food sourcing, shelter building, first aid,
navigation, equipment repair, emergency communication, disaster planning.

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

# Index knowledge base and launch
python main.py index
streamlit run interface/app.py --server.port 8500
```



## Usage

```bash
python main.py index                          # Full index build
python main.py index --incremental            # Add new docs only
python main.py ask "how to purify water"      # Ask a question
python main.py retrieve "shelter" --top-k 8  # Test retrieval
python main.py llm                            # Test raw LLM
```

**Expanding the knowledge base**

Drop any PDF or text file into `raw_docs/` and run:

```bash
python3 main.py index --incremental
```

Only new files are processed. The existing FAISS index is preserved.



## Sample Output

![query1](https://github.com/user-attachments/assets/2e4317cd-ebec-43a2-83f4-7783fd829e55)
![query2](https://github.com/user-attachments/assets/6611765a-5014-44c5-bf93-1d548f8e058e)



## Contributing

Open to modifications, new knowledge domains, and improvements.
If you add something useful, a pull request is welcome.
