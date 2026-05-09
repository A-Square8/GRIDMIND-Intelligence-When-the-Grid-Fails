
# GridMind LLM Engine
# Modular backend abstraction with lazy loading and streaming support.


from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Generator

import requests

logger = logging.getLogger(__name__)


# Abstract base


class LLMBackend(ABC):
    """Abstract base class for LLM inference backends."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        stream: bool = True,
    ) -> str | Generator[str, None, None]:
        """Generate a response from the model.

        When *stream* is True the return value is a generator that yields
        text chunks.  When False a single complete string is returned.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the backend is operational."""



# Ollama backend (REST API)


class OllamaBackend(LLMBackend):
    """Ollama inference via its local REST API."""

    def __init__(
        self,
        model: str = "qwen2.5:3b",
        base_url: str = "http://localhost:11434",
        n_ctx: int = 2048,
        n_threads: int | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._session: requests.Session | None = None



    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

 

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        stream: bool = True,
    ) -> str | Generator[str, None, None]:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "keep_alive": 0,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": self.n_ctx,
                "low_vram": True,
                "num_batch": 256,
            },
        }
        if self.n_threads is not None:
            payload["options"]["num_thread"] = self.n_threads
        if stop:
            payload["options"]["stop"] = stop

        url = f"{self.base_url}/api/generate"
        session = self._get_session()

        if stream:
            return self._stream(session, url, payload)

        t0 = time.perf_counter()
        resp = session.post(url, json=payload, timeout=1200)
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.perf_counter() - t0
        logger.info("Ollama generate: %.1fs", elapsed)
        return data.get("response", "")

    def _stream(
        self,
        session: requests.Session,
        url: str,
        payload: dict,
    ) -> Generator[str, None, None]:
        t0 = time.perf_counter()
        token_count = 0
        with session.post(url, json=payload, stream=True, timeout=1200) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                text = chunk.get("response", "")
                if text:
                    token_count += 1
                    yield text
                if chunk.get("done"):
                    break
        elapsed = time.perf_counter() - t0
        logger.info(
            "Ollama stream: %d chunks in %.1fs (%.1f tok/s)",
            token_count, elapsed,
            token_count / elapsed if elapsed else 0,
        )



    def health_check(self) -> bool:
        try:
            resp = self._get_session().get(
                f"{self.base_url}/api/tags", timeout=5,
            )
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            if self.model not in models:

                base = self.model.split(":")[0]
                if not any(m.startswith(base) for m in models):
                    logger.warning(
                        "Model '%s' not found in Ollama (available: %s)",
                        self.model, models,
                    )
                    return False
            return True
        except Exception as exc:
            logger.error("Ollama health check failed: %s", exc)
            return False



# llama-cpp-python backend (direct GGUF loading)


class LlamaCppBackend(LLMBackend):
    """CPU-only GGUF inference via llama-cpp-python with lazy loading."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        n_threads: int = 2,
        n_gpu_layers: int = 0,
        n_batch: int = 128,
    ) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self._model = None  # lazy


    def _get_model(self):
        if self._model is None:
            from llama_cpp import Llama  

            logger.info("Loading GGUF model from %s …", self.model_path)
            t0 = time.perf_counter()
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                use_mmap=True,
                use_mlock=False,
                verbose=False,
            )
            logger.info("Model loaded in %.1fs", time.perf_counter() - t0)
        return self._model



    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        stream: bool = True,
    ) -> str | Generator[str, None, None]:
        model = self._get_model()

        if stream:
            return self._stream(model, prompt, max_tokens, temperature, top_p, stop)

        t0 = time.perf_counter()
        output = model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
        )
        elapsed = time.perf_counter() - t0
        text = output["choices"][0]["text"]
        logger.info("LlamaCpp generate: %.1fs", elapsed)
        return text

    def _stream(
        self,
        model,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        stop: list[str] | None,
    ) -> Generator[str, None, None]:
        t0 = time.perf_counter()
        token_count = 0
        for chunk in model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
            stream=True,
        ):
            text = chunk["choices"][0]["text"]
            if text:
                token_count += 1
                yield text
        elapsed = time.perf_counter() - t0
        logger.info(
            "LlamaCpp stream: %d tokens in %.1fs (%.1f tok/s)",
            token_count, elapsed,
            token_count / elapsed if elapsed else 0,
        )

  

    def health_check(self) -> bool:
        try:
            model = self._get_model()

            output = model("Hello", max_tokens=1)
            return bool(output["choices"][0]["text"])
        except Exception as exc:
            logger.error("LlamaCpp health check failed: %s", exc)
            return False




_BACKENDS = {
    "ollama": OllamaBackend,
    "llama_cpp": LlamaCppBackend,
}


def create_llm_backend(backend: str = "ollama", **kwargs) -> LLMBackend:
    """Create an LLM backend instance.

    Args:
        backend: One of 'ollama' or 'llama_cpp'.
        **kwargs: Passed directly to the backend constructor.

    Returns:
        An initialised LLMBackend.
    """
    cls = _BACKENDS.get(backend)
    if cls is None:
        raise ValueError(
            f"Unknown backend '{backend}'. Choose from: {list(_BACKENDS)}"
        )
    return cls(**kwargs)
