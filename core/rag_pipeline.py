import os
import json
import time
import logging
from typing import Optional, Iterator
from core.llm_engine import LLMBackend
from core.retriever import ContextRetriever
from core.classifier import UrgencyClassifier
from core.cache import QueryCache
from core.memory import ConversationMemory
from core.relevance_gate import RelevanceGate
from core.concept_graph import ConceptGraph
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_CONTEXT_TOKENS = 1500
_MAX_CHUNK_TOKENS = 500


def _truncate_chunk(text, max_tokens=_MAX_CHUNK_TOKENS):
    words = text.split()
    max_words = int(max_tokens * 0.75)
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " ..."


def _estimate_tokens(text):
    return int(len(text.split()) / 0.75)


class RAGPipeline:
    def __init__(self, llm, retriever, prompt_path="prompts/system_prompt.txt", db=None):
        self.llm = llm
        self.retriever = retriever
        self.classifier = UrgencyClassifier()
        self.cache = QueryCache(capacity=100, db=db, embedder=retriever.embedder)
        self.memory = ConversationMemory(max_turns=3, db=db)
        self.gate = RelevanceGate()
        self.db = db

        store_dir = Path(retriever.store_dir or "data/vector_store")
        self.concept_graph = ConceptGraph()
        concept_path = store_dir / "concepts.json"
        if concept_path.exists():
            self.concept_graph.load(concept_path)

        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def query(self, user_query, top_k=3, domain_filter=None):
        cached_meta = {
            "mode": "SURVIVAL",
            "urgency": "NORMAL",
            "persona": "EXPERT",
            "confidence": "CACHED",
            "procedures_matched": 0,
            "concepts_linked": False,
        }
        cached_meta_str = f"__META__:{json.dumps(cached_meta)}__META_END__\n" + " " * 1024 + "\n"

        cached_response = self.cache.get(user_query)
        if cached_response:
            yield cached_meta_str
            yield cached_response
            return

        semantic_cached = self.cache.get_semantic(user_query)
        if semantic_cached:
            yield cached_meta_str
            yield semantic_cached
            return

        search_queries = self.classifier.extract_search_queries(user_query)

        raw_chunks = []
        sub_k = max(1, (top_k * 2) // len(search_queries)) if search_queries else top_k

        for sq in search_queries:
            raw_chunks.extend(self.retriever.retrieve(sq, top_k=sub_k, domain_filter=domain_filter))

        unique_chunks = {}
        for chunk in raw_chunks:
            if chunk["text"] not in unique_chunks:
                unique_chunks[chunk["text"]] = chunk

        final_chunks = list(unique_chunks.values())[: top_k * 2]

        raw_distances = self.retriever.get_raw_distances(user_query, top_k=top_k)
        gate_result = self.gate.evaluate(user_query, final_chunks, raw_distances)
        confidence_flag = self.gate.format_flag(gate_result)

        ctx = ""
        total_ctx_tokens = 0
        for i, doc in enumerate(final_chunks, 1):
            truncated = _truncate_chunk(doc["text"])
            chunk_tokens = _estimate_tokens(truncated)
            if total_ctx_tokens + chunk_tokens > _MAX_CONTEXT_TOKENS:
                break
            ctx += f"\n--- Source {i} ---\n{truncated}\n"
            total_ctx_tokens += chunk_tokens

        matched_procedures = self.retriever.match_procedures(user_query)
        procedures_ctx = self.retriever.format_procedures_context(matched_procedures)
        if procedures_ctx:
            ctx = procedures_ctx + "\n" + ctx

        concept_ctx = self.concept_graph.format_for_context(user_query)
        if concept_ctx:
            ctx += "\n" + concept_ctx

        classification = self.classifier.classify(user_query)
        class_str = self.classifier.format_for_prompt(classification)

        system_prompt = self.prompt_template.replace("{RETRIEVED_CHUNKS}", ctx)
        system_prompt = system_prompt.replace("{CLASSIFICATION_DATA}", class_str)

        if "{CONFIDENCE_FLAG}" in system_prompt:
            system_prompt = system_prompt.replace("{CONFIDENCE_FLAG}", confidence_flag)
        else:
            system_prompt = system_prompt.replace(
                "{RETRIEVED_CHUNKS}",
                f"{confidence_flag}\n\n{ctx}",
            )

        memory_ctx = self.memory.get_context_string()

        final_prompt = f"{system_prompt}\n\n{memory_ctx}User Question: {user_query}\nAnswer:"

        meta = {
            "mode": classification["mode"],
            "urgency": classification["urgency"],
            "persona": classification["persona"],
            "confidence": gate_result,
            "procedures_matched": len(matched_procedures),
            "concepts_linked": bool(concept_ctx),
        }
        yield f"__META__:{json.dumps(meta)}__META_END__\n" + " " * 1024 + "\n"

        if gate_result == "NO_MATCH":
            no_match_msg = "I do not have reliable information on this topic in my knowledge base. Please consult your physical reference materials or rephrase your question to match a survival domain I cover: water purification, first aid, shelter, fire, food, navigation, or emergency communication."
            self.cache.put(user_query, no_match_msg)
            self.memory.add_interaction(user_query, no_match_msg, meta)
            yield no_match_msg
            return

        try:
            response_chunks = []
            for chunk in self.llm.generate(final_prompt, stop=["[SYS] Output complete.", "[SYS] Output complete", "Answer:"]):
                response_chunks.append(chunk)
                yield chunk

            full_response = "".join(response_chunks)

            query_embedding = None
            try:
                query_embedding = self.retriever._get_embedding(user_query)
            except Exception:
                pass

            self.cache.put(user_query, full_response, query_embedding)
            self.memory.add_interaction(user_query, full_response, meta)

        except Exception as e:
            logger.error("LLM generation failed: %s. Retrying...", e)
            time.sleep(3)
            try:
                response_chunks = []
                for chunk in self.llm.generate(final_prompt, stop=["[SYS] Output complete.", "[SYS] Output complete", "Answer:"]):
                    response_chunks.append(chunk)
                    yield chunk
                full_response = "".join(response_chunks)
                self.cache.put(user_query, full_response)
                self.memory.add_interaction(user_query, full_response, meta)
            except Exception as e2:
                logger.error("LLM retry failed: %s", e2)
                error_msg = "System error: LLM generation failed after retry. Please try again."
                yield error_msg

    def set_conversation(self, conversation_id):
        self.memory.set_conversation(conversation_id)

    def clear_memory(self):
        self.memory.clear()
