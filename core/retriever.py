from typing import Optional
import logging
import numpy as np
from ingestion.indexer import load_index
from core.embeddings import OllamaEmbedder

logger = logging.getLogger(__name__)

class ContextRetriever:
    def __init__(self, embedder: Optional[OllamaEmbedder] = None, store_dir: Optional[str] = None):
        self.index, self.metadata = load_index(store_dir)
        self.embedder = embedder or OllamaEmbedder()

    def retrieve(self, query: str, top_k: int = 5, domain_filter: Optional[str] = None) -> list[dict]:
        query_vec = np.expand_dims(self.embedder.embed(query), axis=0)
        search_k = max(50, top_k * 5) if domain_filter else top_k
        distances, indices = self.index.search(query_vec, search_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1: continue
            meta = self.metadata[idx]
            if domain_filter and meta["domain"] != domain_filter: continue
            
            res = dict(meta)
            res["score"] = float(dist)
            results.append(res)
            if len(results) >= top_k: break
            
        return results
