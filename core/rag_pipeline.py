import os
from typing import Optional, Iterator
from core.llm_engine import LLMBackend
from core.retriever import ContextRetriever
from core.classifier import UrgencyClassifier

# Maximum tokens of retrieved context to inject into the prompt.
# Keeps the prompt within the reduced 1024 n_ctx window with room for
# system prompt (~200 tokens) + response generation.
_MAX_CONTEXT_TOKENS = 1500
_MAX_CHUNK_TOKENS = 500


def _truncate_chunk(text: str, max_tokens: int = _MAX_CHUNK_TOKENS) -> str:
    """Truncate a chunk to approximately max_tokens using word-count heuristic."""
    words = text.split()
    # ~0.75 words per token
    max_words = int(max_tokens * 0.75)
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"


def _estimate_tokens(text: str) -> int:
    """Quick token estimate: word_count / 0.75."""
    return int(len(text.split()) / 0.75)


class RAGPipeline:
    def __init__(self, llm: LLMBackend, retriever: ContextRetriever, prompt_path: str = "prompts/system_prompt.txt"):
        self.llm = llm
        self.retriever = retriever
        self.classifier = UrgencyClassifier()
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def query(self, user_query: str, top_k: int = 3, domain_filter: Optional[str] = None) -> Iterator[str]:
        print("\n[*] Retrieving context chunks from local vector store...")
        
        # Extract narrative clusters
        search_queries = self.classifier.extract_search_queries(user_query)
        print(f"[*] Decomposed query into {len(search_queries)} search vectors.")
        
        raw_chunks = []
        sub_k = max(1, (top_k * 2) // len(search_queries)) if search_queries else top_k
        
        for sq in search_queries:
            raw_chunks.extend(self.retriever.retrieve(sq, top_k=sub_k, domain_filter=domain_filter))
            
        # Deduplicate
        unique_chunks = {}
        for chunk in raw_chunks:
            if chunk['text'] not in unique_chunks:
                unique_chunks[chunk['text']] = chunk
                
        # Limit to 2x requested top K to aggressively cap context window
        final_chunks = list(unique_chunks.values())[:top_k * 2]
        
        # Build context with per-chunk truncation and total token cap
        ctx = ""
        total_ctx_tokens = 0
        for i, doc in enumerate(final_chunks, 1):
            truncated = _truncate_chunk(doc['text'])
            chunk_tokens = _estimate_tokens(truncated)
            if total_ctx_tokens + chunk_tokens > _MAX_CONTEXT_TOKENS:
                # Reached the cap — stop adding more context
                break
            ctx += f"\n--- Source {i} ---\n{truncated}\n"
            total_ctx_tokens += chunk_tokens
            
        classification = self.classifier.classify(user_query)
        class_str = self.classifier.format_for_prompt(classification)
        
        system_prompt = self.prompt_template.replace("{RETRIEVED_CHUNKS}", ctx)
        system_prompt = system_prompt.replace("{CLASSIFICATION_DATA}", class_str)
        
        final_prompt = f"{system_prompt}\n\nUser Question: {user_query}\nAnswer:"
        
        print(f"[*] Context retrieved! Prompt length is {len(final_prompt)} characters (~{_estimate_tokens(final_prompt)} tokens).")
        print(f"[*] Classifier detected: {class_str.replace(chr(10), ' | ')}")
        print("[*] LLM analyzing context... (This will take a few minutes on constrained RAM)\n")
        return self.llm.generate(final_prompt)
