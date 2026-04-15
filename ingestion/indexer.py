import json
import logging
import time
from pathlib import Path
import faiss
import numpy as np
from core.embeddings import OllamaEmbedder

logger = logging.getLogger(__name__)
DEFAULT_STORE_DIR = Path(__file__).resolve().parent.parent / "data" / "vector_store"

def build_index(chunks: list[dict], embedder: OllamaEmbedder, batch_size: int = 32, output_dir: str | Path | None = None):
    store = Path(output_dir or DEFAULT_STORE_DIR)
    store.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    vectors = embedder.embed_batch([c["text"] for c in chunks], batch_size=batch_size)
    embed_time = time.perf_counter() - t0
    
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    
    metadata = [{"chunk_id": c["chunk_id"], "source_file": c["source_file"], "domain": c["domain"], "text": c["text"], "token_count": c["token_count"]} for c in chunks]
    faiss.write_index(index, str(store / "index.faiss"))
    with open(store / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)
        
    idx_size, meta_size = (store / "index.faiss").stat().st_size, (store / "metadata.json").stat().st_size
    logger.info("Index built: %d vectors, dim=%d, embed=%.1fs, index=%.1fMB, metadata=%.1fMB", index.ntotal, dim, embed_time, idx_size / 1e6, meta_size / 1e6)
    return index, metadata

def load_index(store_dir: str | Path | None = None):
    store = Path(store_dir or DEFAULT_STORE_DIR)
    index = faiss.read_index(str(store / "index.faiss"))
    with open(store / "metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    logger.info("Loaded index: %d vectors", index.ntotal)
    return index, metadata
