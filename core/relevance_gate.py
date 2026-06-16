import numpy as np
import logging

logger = logging.getLogger(__name__)


class RelevanceGate:
    def __init__(self, distance_threshold=0.72, keyword_overlap_threshold=0.15):
        self.distance_threshold = distance_threshold
        self.keyword_overlap_threshold = keyword_overlap_threshold
        self.stopwords = {
            "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
            "they", "them", "what", "which", "who", "this", "that", "these",
            "am", "is", "are", "was", "were", "be", "been", "have", "has",
            "had", "do", "does", "did", "a", "an", "the", "and", "but", "if",
            "or", "as", "of", "at", "by", "for", "with", "about", "to", "from",
            "in", "out", "on", "off", "up", "down", "how", "can", "will",
            "just", "should", "now", "tell", "give", "show", "help", "need",
            "explain", "describe", "find", "want", "would", "could",
        }

    def evaluate(self, query, chunks, distances=None):
        if not chunks:
            return "NO_MATCH"

        if distances is not None and len(distances) > 0:
            best_distance = min(distances)
            if best_distance > self.distance_threshold:
                return "NO_MATCH"

        # Strip punctuation from query words for clean matching
        query_words = set()
        for w in query.split():
            clean_w = "".join(char for char in w if char.isalnum()).lower()
            if clean_w not in self.stopwords and len(clean_w) > 2:
                query_words.add(clean_w)

        if not query_words:
            return "PASS"

        # Strip punctuation from chunk words
        chunk_text = " ".join(c.get("text", "") for c in chunks).lower()
        chunk_words = set(
            "".join(char for char in w if char.isalnum())
            for w in chunk_text.split()
        )

        overlap = len(query_words & chunk_words) / len(query_words)

        if overlap < self.keyword_overlap_threshold:
            return "LOW_CONFIDENCE"

        return "PASS"

    def format_flag(self, gate_result):
        if gate_result == "NO_MATCH":
            return "CONFIDENCE: NONE - No relevant source material was found for this query. Do NOT answer this question. Instead, respond with: 'I do not have reliable information on this topic in my knowledge base.'"
        elif gate_result == "LOW_CONFIDENCE":
            return "CONFIDENCE: LOW - Retrieved sources have weak relevance. Begin your response with '[LOW CONFIDENCE]' and clearly flag which parts are extrapolated versus sourced."
        return "CONFIDENCE: HIGH - Retrieved sources are relevant."
