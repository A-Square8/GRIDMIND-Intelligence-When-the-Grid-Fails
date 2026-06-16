import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Iterator
from core.llm_engine import create_llm_backend
from core.retriever import ContextRetriever
from core.rag_pipeline import RAGPipeline

class GridMindAPI:
    def __init__(self, llm_backend: str = "ollama", model_path: str = "", store_dir: str = "data/vector_store"):
        if llm_backend == "llamacpp":
             self.llm = create_llm_backend(backend=llm_backend, model_path=model_path)
        else:
             self.llm = create_llm_backend(backend=llm_backend)
             
        self.retriever = ContextRetriever(store_dir=store_dir)
        self.pipeline = RAGPipeline(self.llm, self.retriever, prompt_path="prompts/system_prompt.txt")

    def query(self, text: str, top_k: int = 3, domain: Optional[str] = None) -> Iterator[str]:
        return self.pipeline.query(text, top_k=top_k, domain_filter=domain)
