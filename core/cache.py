import time
import hashlib
import numpy as np


class QueryCache:
    def __init__(self, capacity=100, db=None, embedder=None):
        self.capacity = capacity
        self.cache = {}
        self.db = db
        self.embedder = embedder
        self._embed_cache = {}

    def _hash_query(self, query):
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]

    def get(self, query):
        q_lower = query.lower().strip()

        if q_lower in self.cache:
            item = self.cache.pop(q_lower)
            self.cache[q_lower] = item
            return item["response"]

        if self.db:
            q_hash = self._hash_query(query)
            cached = self.db.cache_get(q_hash)
            if cached:
                return cached

        return None

    def get_semantic(self, query):
        if not self.embedder:
            return None

        try:
            query_vec = self.embedder.embed(query)
        except Exception:
            return None

        best_score = 0
        best_response = None

        for key, item in self.cache.items():
            if "embedding" in item and item["embedding"] is not None:
                sim = self._cosine_similarity(query_vec, item["embedding"])
                if sim > best_score:
                    best_score = sim
                    best_response = item["response"]

        if self.db:
            for q_hash, emb, response in self.db.get_all_cache_embeddings():
                sim = self._cosine_similarity(query_vec, emb)
                if sim > best_score:
                    best_score = sim
                    best_response = response

        if best_score > 0.92:
            return best_response

        return None

    def put(self, query, response, query_embedding=None):
        q_lower = query.lower().strip()

        if q_lower in self.cache:
            self.cache.pop(q_lower)
        elif len(self.cache) >= self.capacity:
            self.cache.pop(next(iter(self.cache)))

        self.cache[q_lower] = {
            "response": response,
            "timestamp": time.time(),
            "embedding": query_embedding,
        }

        if self.db:
            q_hash = self._hash_query(query)
            self.db.cache_put(q_hash, response, query_embedding)

    def _cosine_similarity(self, a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
