import pickle
import logging
from pathlib import Path
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Index:
    def __init__(self):
        self.index = None
        self.tokenized_corpus = []

    def build(self, texts):
        self.tokenized_corpus = [text.lower().split() for text in texts]
        if self.tokenized_corpus:
            self.index = BM25Okapi(self.tokenized_corpus)

    def search(self, query, top_k=5):
        if self.index is None:
            return []
        tokenized_query = query.lower().split()
        scores = self.index.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(idx, float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"corpus": self.tokenized_corpus}, f)
        logger.info("BM25 index saved to %s", path)

    def load(self, path):
        path = Path(path)
        if not path.exists():
            logger.warning("BM25 index not found at %s", path)
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.tokenized_corpus = data["corpus"]
        if self.tokenized_corpus:
            self.index = BM25Okapi(self.tokenized_corpus)
        logger.info("BM25 index loaded: %d documents", len(self.tokenized_corpus))
        return True

    def append(self, texts):
        new_tokens = [text.lower().split() for text in texts]
        self.tokenized_corpus.extend(new_tokens)
        if self.tokenized_corpus:
            self.index = BM25Okapi(self.tokenized_corpus)
