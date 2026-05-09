import json
import logging
import time
from typing import Sequence
import numpy as np
import requests

logger = logging.getLogger(__name__)

class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._session = None
        self._dim = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = self.embed("ping").shape[0]
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        resp = self._get_session().post(
            f"{self.base_url}/api/embed", json={"model": self.model, "input": text, "keep_alive": 0}, timeout=120)
        resp.raise_for_status()
        return np.array(resp.json()["embeddings"][0], dtype=np.float32)

    def embed_batch(self, texts: Sequence[str], batch_size: int = 8) -> np.ndarray:
        all_vecs = []
        total = len(texts)
        t0 = time.perf_counter()
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = [t.replace("\x00", "") for t in texts[start:end]]
            try:
                resp = self._get_session().post(
                    f"{self.base_url}/api/embed", json={"model": self.model, "input": batch, "keep_alive": 0}, timeout=3600)
                resp.raise_for_status()
                all_vecs.append(np.array(resp.json()["embeddings"], dtype=np.float32))
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 400:
                    batch_vecs = []
                    for t in batch:
                        try:
                            r = self._get_session().post(
                                f"{self.base_url}/api/embed", json={"model": self.model, "input": t}, timeout=3600)
                            r.raise_for_status()
                            batch_vecs.append(r.json()["embeddings"][0])
                        except requests.exceptions.HTTPError as e2:
                            if e2.response is not None and e2.response.status_code == 400:
                                try:
                                    r = self._get_session().post(f"{self.base_url}/api/embed", json={"model": self.model, "input": t[:2000]}, timeout=3600)
                                    r.raise_for_status()
                                    batch_vecs.append(r.json()["embeddings"][0])
                                except Exception:
                                    logger.warning("Chunk completely failed, substituting zero-vector.")
                                    batch_vecs.append([0.0] * self.dim)
                            else:
                                raise e2
                    all_vecs.append(np.array(batch_vecs, dtype=np.float32))
                else:
                    raise e
            logger.info("Embedded %d/%d (%.1fs elapsed)", end, total, time.perf_counter() - t0)
        
        result = np.vstack(all_vecs)
        if self._dim is None:
            self._dim = result.shape[1]
        return result
