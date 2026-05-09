from typing import Optional
import logging
from functools import lru_cache
import numpy as np
from ingestion.indexer import load_index, load_chunk_texts
from core.embeddings import OllamaEmbedder

logger = logging.getLogger(__name__)

class ContextRetriever:
    def __init__(self, embedder: Optional[OllamaEmbedder] = None, store_dir: Optional[str] = None):
        self.index, self.metadata = load_index(store_dir)
        self.embedder = embedder or OllamaEmbedder()
        self.store_dir = store_dir
        # Simple cache for recent query embeddings to avoid redundant API calls
        # when RAG pipeline decomposes a query into multiple search vectors
        self._embed_cache: dict[str, np.ndarray] = {}
        self._cache_max = 32

    def _get_embedding(self, query: str) -> np.ndarray:
        """Get embedding for a query, using cache to avoid redundant Ollama calls."""
        if query in self._embed_cache:
            return self._embed_cache[query]
        vec = self.embedder.embed(query)
        # Evict oldest if cache is full
        if len(self._embed_cache) >= self._cache_max:
            oldest_key = next(iter(self._embed_cache))
            del self._embed_cache[oldest_key]
        self._embed_cache[query] = vec
        return vec

    def retrieve(self, query: str, top_k: int = 5, domain_filter: Optional[str] = None) -> list[dict]:
        query_vec = np.expand_dims(self._get_embedding(query), axis=0)
        search_k = max(50, top_k * 5) if domain_filter else top_k
        distances, indices = self.index.search(query_vec, search_k)
        
        # Collect matching indices first (without text)
        matched = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1: continue
            meta = self.metadata[idx]
            if domain_filter and meta["domain"] != domain_filter: continue
            matched.append((idx, dist, meta))
            if len(matched) >= top_k: break

        if not matched:
            return []

        # Lazy-load text only for the matched chunks
        needed_indices = [idx for idx, _, _ in matched]
        texts = load_chunk_texts(needed_indices, self.store_dir)

        results = []
        for idx, dist, meta in matched:
            res = dict(meta)
            res["text"] = texts.get(idx, "")
            res["score"] = float(dist)
            results.append(res)
            
        return results
