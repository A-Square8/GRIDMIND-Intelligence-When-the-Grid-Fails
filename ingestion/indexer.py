import json
import logging
import time
from pathlib import Path
import faiss
import numpy as np
from core.embeddings import OllamaEmbedder
from core.bm25_index import BM25Index

logger = logging.getLogger(__name__)
DEFAULT_STORE_DIR = Path(__file__).resolve().parent.parent / "data" / "vector_store"


def build_index(chunks, embedder, batch_size=8, output_dir=None):
    store = Path(output_dir or DEFAULT_STORE_DIR)
    store.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    vectors = embedder.embed_batch([c["text"] for c in chunks], batch_size=batch_size)
    embed_time = time.perf_counter() - t0

    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    metadata = [
        {
            "chunk_id": c["chunk_id"],
            "source_file": c["source_file"],
            "domain": c["domain"],
            "text": c["text"],
            "token_count": c["token_count"],
        }
        for c in chunks
    ]
    faiss.write_index(index, str(store / "index.faiss"))
    with open(store / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    bm25 = BM25Index()
    bm25.build([c["text"] for c in chunks])
    bm25.save(store / "bm25.pkl")

    idx_size = (store / "index.faiss").stat().st_size
    meta_size = (store / "metadata.json").stat().st_size
    logger.info(
        "Index built: %d vectors, dim=%d, embed=%.1fs, index=%.1fMB, metadata=%.1fMB",
        index.ntotal, dim, embed_time, idx_size / 1e6, meta_size / 1e6,
    )
    return index, metadata


def load_index(store_dir=None):
    store = Path(store_dir or DEFAULT_STORE_DIR)
    index = faiss.read_index(str(store / "index.faiss"), faiss.IO_FLAG_MMAP)
    with open(store / "metadata.json", "r", encoding="utf-8") as f:
        raw_metadata = json.load(f)

    metadata = []
    for entry in raw_metadata:
        metadata.append(
            {
                "chunk_id": entry["chunk_id"],
                "source_file": entry["source_file"],
                "domain": entry["domain"],
                "token_count": entry["token_count"],
            }
        )

    logger.info(
        "Loaded index: %d vectors (mmap), metadata: %d entries (text-stripped)",
        index.ntotal, len(metadata),
    )
    return index, metadata


def load_chunk_texts(indices, store_dir=None):
    store = Path(store_dir or DEFAULT_STORE_DIR)
    needed = set(indices)

    texts = {}
    with open(store / "metadata.json", "r", encoding="utf-8") as f:
        all_meta = json.load(f)

    for idx in needed:
        if 0 <= idx < len(all_meta):
            texts[idx] = all_meta[idx].get("text", "")

    return texts


def incremental_index(docs_dir, embedder, batch_size=8, store_dir=None):
    from ingestion.watcher import FileWatcher
    from ingestion.loader import load_documents
    from ingestion.chunker import chunk_documents

    store = Path(store_dir or DEFAULT_STORE_DIR)
    store.mkdir(parents=True, exist_ok=True)

    logger.info("Checking for new documents for incremental index...")
    manifest_path = store / "file_manifest.json"
    watcher = FileWatcher(manifest_path)

    new_files = watcher.scan(docs_dir)
    if not new_files:
        logger.info("No new or modified files found. Vector store is up-to-date.")
        return None, None

    logger.info("Found %d new/modified files. Extracting...", len(new_files))
    documents = load_documents(docs_dir, target_files=new_files)
    if not documents:
        logger.warning("No texts could be extracted from new files.")
        return None, None

    chunks = chunk_documents(documents)
    if not chunks:
        logger.warning("No chunks generated from extracted documents.")
        return None, None

    index_path = store / "index.faiss"
    metadata_path = store / "metadata.json"

    if index_path.exists() and metadata_path.exists():
        index = faiss.read_index(str(index_path))
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        index = None
        metadata = []

    logger.info("Embedding %d new chunks...", len(chunks))
    t0 = time.perf_counter()
    new_vectors = embedder.embed_batch([c["text"] for c in chunks], batch_size=batch_size)
    embed_time = time.perf_counter() - t0

    dim = new_vectors.shape[1]

    if index is None:
        index = faiss.IndexFlatL2(dim)

    index.add(new_vectors)

    new_meta = [
        {
            "chunk_id": c["chunk_id"],
            "source_file": c["source_file"],
            "domain": c["domain"],
            "text": c["text"],
            "token_count": c["token_count"],
        }
        for c in chunks
    ]
    metadata.extend(new_meta)

    faiss.write_index(index, str(index_path))
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    bm25 = BM25Index()
    all_texts = [m.get("text", "") for m in metadata]
    bm25.build(all_texts)
    bm25.save(store / "bm25.pkl")

    watcher.save_manifest()

    idx_size = index_path.stat().st_size
    meta_size = metadata_path.stat().st_size
    logger.info(
        "Incremental update complete: Added %d chunks in %.1fs. Total vectors: %d (%.1fMB index)",
        len(chunks), embed_time, index.ntotal, idx_size / 1e6,
    )
    return index, metadata
