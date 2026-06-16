import os
from typing import Optional, Iterator
from core.llm_engine import LLMBackend
from core.retriever import ContextRetriever
from core.classifier import UrgencyClassifier
from core.cache import QueryCache
from core.memory import ConversationMemory

_MAX_CONTEXT_TOKENS = 1500
_MAX_CHUNK_TOKENS = 500

def _truncate_chunk(text: str, max_tokens: int = _MAX_CHUNK_TOKENS) -> str:
    words = text.split()
    max_words = int(max_tokens * 0.75)
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"

def _estimate_tokens(text: str) -> int:
    return int(len(text.split()) / 0.75)

class RAGPipeline:
    def __init__(self, llm: LLMBackend, retriever: ContextRetriever, prompt_path: str = "prompts/system_prompt.txt"):
        self.llm = llm
        self.retriever = retriever
        self.classifier = UrgencyClassifier()
        self.cache = QueryCache(capacity=100)
        self.memory = ConversationMemory(max_turns=3)
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def query(self, user_query: str, top_k: int = 3, domain_filter: Optional[str] = None) -> Iterator[str]:
        cached_response = self.cache.get(user_query)
        if cached_response:
            yield cached_response
            return
            
        search_queries = self.classifier.extract_search_queries(user_query)
        
        raw_chunks = []
        sub_k = max(1, (top_k * 2) // len(search_queries)) if search_queries else top_k
        
        for sq in search_queries:
            raw_chunks.extend(self.retriever.retrieve(sq, top_k=sub_k, domain_filter=domain_filter))
            
        unique_chunks = {}
        for chunk in raw_chunks:
            if chunk['text'] not in unique_chunks:
                unique_chunks[chunk['text']] = chunk
                
        final_chunks = list(unique_chunks.values())[:top_k * 2]
        
        ctx = ""
        total_ctx_tokens = 0
        for i, doc in enumerate(final_chunks, 1):
            truncated = _truncate_chunk(doc['text'])
            chunk_tokens = _estimate_tokens(truncated)
            if total_ctx_tokens + chunk_tokens > _MAX_CONTEXT_TOKENS:
                break
            ctx += f"\n--- Source {i} ---\n{truncated}\n"
            total_ctx_tokens += chunk_tokens
            
        classification = self.classifier.classify(user_query)
        class_str = self.classifier.format_for_prompt(classification)
        
        system_prompt = self.prompt_template.replace("{RETRIEVED_CHUNKS}", ctx)
        system_prompt = system_prompt.replace("{CLASSIFICATION_DATA}", class_str)
        
        memory_ctx = self.memory.get_context_string()
        
        final_prompt = f"{system_prompt}\n\n{memory_ctx}User Question: {user_query}\nAnswer:"
        
        response_chunks = []
        for chunk in self.llm.generate(final_prompt):
            response_chunks.append(chunk)
            yield chunk
            
        full_response = "".join(response_chunks)
        self.cache.put(user_query, full_response)
        self.memory.add_interaction(user_query, full_response)

    def clear_memory(self):
        self.memory.clear()
