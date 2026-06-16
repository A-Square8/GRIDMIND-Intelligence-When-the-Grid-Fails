from typing import Optional
import logging
import numpy as np
from pathlib import Path
from ingestion.indexer import load_index, load_chunk_texts
from core.embeddings import OllamaEmbedder
from core.bm25_index import BM25Index
from ingestion.procedure_extractor import load_procedures

logger = logging.getLogger(__name__)

DEFAULT_STORE_DIR = Path(__file__).resolve().parent.parent / "data" / "vector_store"


class ContextRetriever:
    def __init__(self, embedder=None, store_dir=None):
        self.store_dir = store_dir
        store_path = Path(store_dir or DEFAULT_STORE_DIR)
        self.index, self.metadata = load_index(store_dir)
        self.embedder = embedder or OllamaEmbedder()
        self._embed_cache = {}
        self._cache_max = 32

        self.bm25 = BM25Index()
        bm25_path = store_path / "bm25.pkl"
        self.bm25.load(bm25_path)

        self.procedures = load_procedures(store_path / "procedures.json")

    def _get_embedding(self, query):
        if query in self._embed_cache:
            return self._embed_cache[query]
        vec = self.embedder.embed(query)
        if len(self._embed_cache) >= self._cache_max:
            oldest_key = next(iter(self._embed_cache))
            del self._embed_cache[oldest_key]
        self._embed_cache[query] = vec
        return vec

    def retrieve(self, query, top_k=5, domain_filter=None):
        query_vec = np.expand_dims(self._get_embedding(query), axis=0)
        faiss_k = max(50, top_k * 5) if domain_filter else top_k * 3
        distances, indices = self.index.search(query_vec, faiss_k)

        faiss_ranked = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            if domain_filter and meta["domain"] != domain_filter:
                continue
            faiss_ranked.append((int(idx), float(dist)))

        bm25_ranked = self.bm25.search(query, top_k=top_k * 3)

        if bm25_ranked:
            merged = self._rrf_merge(faiss_ranked, bm25_ranked, top_k * 2)
        else:
            merged = [(idx, dist) for idx, dist in faiss_ranked[:top_k * 2]]

        if domain_filter:
            merged = [
                (idx, score) for idx, score in merged
                if 0 <= idx < len(self.metadata) and self.metadata[idx]["domain"] == domain_filter
            ]

        final_indices = [idx for idx, _ in merged[:top_k]]
        final_distances = [score for _, score in merged[:top_k]]

        if not final_indices:
            return []

        texts = load_chunk_texts(final_indices, self.store_dir)

        results = []
        for idx, score in zip(final_indices, final_distances):
            if idx >= len(self.metadata):
                continue
            res = dict(self.metadata[idx])
            res["text"] = texts.get(idx, "")
            res["score"] = score
            results.append(res)

        return results

    def get_raw_distances(self, query, top_k=5):
        query_vec = np.expand_dims(self._get_embedding(query), axis=0)
        distances, _ = self.index.search(query_vec, top_k)
        return distances[0].tolist()

    def match_procedures(self, query, max_results=3):
        if not self.procedures:
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for proc in self.procedures:
            title = proc.get("title", "").lower()
            title_words = set(title.split())
            if not title_words:
                continue
            overlap = len(query_words & title_words)
            if overlap > 0:
                score = overlap / len(title_words)
                scored.append((score, proc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [proc for _, proc in scored[:max_results] if _[0] > 0.3]

    def format_procedures_context(self, procedures):
        if not procedures:
            return ""

        lines = []
        for proc in procedures:
            lines.append(f"--- MATCHED PROCEDURE: {proc.get('title', 'Unknown')} ---")
            requires = proc.get("requires", [])
            if requires:
                lines.append(f"Requires: {', '.join(requires)}")
            steps = proc.get("steps", [])
            for j, step in enumerate(steps, 1):
                lines.append(f"  {j}. {step}")
            danger = proc.get("danger")
            if danger:
                lines.append(f"WARNING: {danger}")
            lines.append("--- END PROCEDURE ---")
        return "\n".join(lines)

    def _rrf_merge(self, faiss_ranked, bm25_ranked, top_k, k=60):
        scores = {}

        for rank, (idx, _) in enumerate(faiss_ranked):
            scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)

        for rank, (idx, _) in enumerate(bm25_ranked):
            scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)

        sorted_indices = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(idx, score) for idx, score in sorted_indices[:top_k]]
