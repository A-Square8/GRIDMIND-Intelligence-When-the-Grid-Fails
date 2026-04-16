# GridMind Construction & Operation Instructions

This guide provides the necessary steps to set up, test, and expand the GridMind offline survival assistant.

## 1. Initial Setup
Assumes you have Python 3.10+ installed and the repository downloaded.

### Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Backend Setup (Choose One)

#### Option A: Ollama (Easiest / Recommended)
Ollama provides a simple REST API and easy model management.
1.  **Download & Install:** Visit [ollama.com](https://ollama.com/) and follow the install instructions for your OS.
2.  **Pull Required Weights:** Open your terminal and run:
    ```bash
    ollama pull qwen2.5:3b        # For text generation
    ollama pull nomic-embed-text # For document embeddings
    ```
3.  **Verify Service:** Ensure the Ollama service is running (check your system tray or run `ollama list`).

#### Option B: llama-cpp-python (Local GGUF)
Ideal for fine-grained CPU control or if you have pre-downloaded GGUF files.
1.  **Download Model:** Obtain a Qwen 2.5 3B Instruct GGUF file from HuggingFace.
2.  **Organize Files:** Place the file in a `models/` directory within the project.
3.  **CLI Usage:** You must explicitly point GridMind to the file using the `--model-path` flag:
    ```bash
    python3 main.py ask "Your query" --llm llamacpp --model-path ./models/qwen2.5-3b-instruct.gguf
    ```

---

## 2. Terminal Testing

### Stage 4: Test the Retrieval System
Verify that the vector store can find relevant survival context.
```bash
python3 main.py retrieve "How to perform cpr" --top-k 8
```

### Stage 6: Test RAG + LLM Response
Verify the end-to-end pipeline (Retrieval + Inference).
```bash
python3 main.py ask "What are the early signs of radiation sickness?"
```

---

## 3. Launching the GUI
To start the brutalist terminal-style dashboard:
```bash
streamlit run interface/app.py --server.port 8500
```

---

## 4. Expanding Knowledge (Adding New Data)
GridMind supports ultra-fast incremental updates without rebuilding the entire index.

1.  **Paste Folders:** Drop your new document folders (e.g., `03_water`, `04_tools`) into the `raw_docs/` directory.
2.  **Sync Index:** Run the incremental update command:
    ```bash
    python3 main.py index --incremental
    ```
    The system will automatically detect only the new/modified files via SHA-256 hashing and append them to the existing FAISS brain.

---


