# **GridMind: Intelligence When the Grid Fails**

## **Overview**
GridMind is an offline AI survival assistant that works without internet. It stores knowledge across multiple areas such as water purification, food finding, shelter building, first aid, navigation, repair skills, communication, and emergency planning. New documents can be added anytime, and the system updates its knowledge without rebuilding everything from scratch. It is optimized to run on normal CPU hardware, making it useful on laptops or low-power devices. GridMind also includes a clean terminal-style dashboard for fast and practical use in off-grid situations.

## **Models & Infrastructure**

| Component | Technology / Model | Purpose |
| :--- | :--- | :--- |
| **Generative Model** | `qwen2.5:3b` | Used via Ollama or `llama.cpp` for core LLM inference and response generation. |
| **Embedding Model** | `nomic-embed-text` | Generates document embeddings locally to facilitate semantic search. |
| **Vector Store** | `FAISS (cpu)` | Enables high-speed, CPU-optimized vector similarity search for retrieving offline context. |

## **Dependencies**
- **Python 3.10+**
- `llama-cpp-python>=0.3.0`
- `requests>=2.31.0`
- `pdfplumber>=0.10.0`
- `faiss-cpu>=1.7.4`
- `streamlit`

*See `requirements.txt` for complete environment details.*

## **System Architecture**

<img width="1599" height="929" alt="image" src="https://github.com/user-attachments/assets/12fd8f1d-28af-4778-9d96-3cd6e246713e" />


## **Instructions**

**1. Setup Environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Select and Configure Backend (Ollama Recommended)**
**Download & Install:** Visit [ollama.com](https://ollama.com/) and follow the install instructions for your OS.
**Pull Required Weights:** Open your terminal and run:
    ```bash
    ollama pull qwen2.5:3b        # For text generation
    ollama pull nomic-embed-text # For document embeddings
    ```
**Verify Service:** Ensure the Ollama service is running (check your system tray or run `ollama list`).


**3. Launch the Assistant**
```bash
streamlit run interface/app.py --server.port 8500
```

**4. CLI commands**
```bash
python main.py index                    # Full indexing
python main.py index --incremental      # Incremental update
python main.py ask "your question"      # Get RAG-powered answer
python main.py retrieve "query" --top-k 8   # Test retrieval only
python main.py llm                      # Test raw LLM
```

## **Note: Knowledge Base Modification**
Users are completely free to modify, customize, and add to the knowledge base as they see fit to tailor GridMind to their specific survival scenarios.

You can instantly expand the offline knowledge base by adding relevant documents, books, or field manuals into the `raw_docs/` folder. Afterward, run:

```bash
python3 main.py index --incremental
```

This triggers the optimized incremental indexing process using SHA-256 hashing. It will only process the new additions and merge them seamlessly into the existing FAISS vector database.

<img width="1917" height="914" alt="sample_query1" src="https://github.com/user-attachments/assets/2e4317cd-ebec-43a2-83f4-7783fd829e55" />

<img width="1654" height="805" alt="sample_query2" src="https://github.com/user-attachments/assets/6611765a-5014-44c5-bf93-1d548f8e058e" />


## **Note**
GridMind is open for the community to modify, expand, and experiment with based on their own needs and survival scenarios. Users can add new documents, improve existing knowledge, or adapt the system for different environments and use cases. Credit for all source books, manuals, and reference materials belongs to their respective authors and publishers.
