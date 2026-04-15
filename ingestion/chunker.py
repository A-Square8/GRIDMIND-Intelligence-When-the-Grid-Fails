"""
GridMind Document Chunker — Stage 2
Token-aware text chunking with overlap and metadata attachment.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Approximation: 1 token ≈ 0.75 words (conservative for English text).
_WORDS_PER_TOKEN = 0.75


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in *text* using word-count heuristic."""
    word_count = len(text.split())
    return int(word_count / _WORDS_PER_TOKEN)


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])"  # split after sentence-ending punct + space + capital
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (best effort)."""
    sentences = _SENTENCE_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split *text* into chunks of approximately *chunk_size* tokens.

    Uses sentence boundaries where possible. Each chunk overlaps with the
    previous one by approximately *chunk_overlap* tokens.

    Args:
        text: The full text to chunk.
        chunk_size: Target chunk size in tokens (aim for 300–500).
        chunk_overlap: Overlap between consecutive chunks in tokens.

    Returns:
        A list of text chunks.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sent_tokens = estimate_tokens(sentence)

        # If a single sentence exceeds chunk_size, force-split by words
        if sent_tokens > chunk_size:
            # Flush current buffer first
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_tokens = 0

            words = sentence.split()
            target_words = int(chunk_size * _WORDS_PER_TOKEN)
            for i in range(0, len(words), target_words):
                chunk_words = words[i : i + target_words]
                chunks.append(" ".join(chunk_words))
            continue

        # Would adding this sentence exceed the target?
        if current_tokens + sent_tokens > chunk_size and current_sentences:
            chunks.append(" ".join(current_sentences))

            # Build overlap from the tail of current_sentences
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                st = estimate_tokens(s)
                if overlap_tokens + st > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += st

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sent_tokens

    # Flush remaining
    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


# ---------------------------------------------------------------------------
# Document chunking with metadata
# ---------------------------------------------------------------------------

def _make_chunk_id(domain: str, filename: str, index: int) -> str:
    """Create a deterministic chunk ID from domain, filename, and index."""
    stem = Path(filename).stem
    # Sanitise for use as an ID component
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:60]
    return f"{domain}__{safe_stem}__{index:04d}"


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 400,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Chunk a list of document dicts and attach metadata.

    Each input dict must have keys: ``text``, ``path``, ``domain``.

    Returns a list of chunk dicts with keys:
        ``chunk_id``, ``text``, ``source_file``, ``domain``, ``token_count``.
    """
    all_chunks: list[dict] = []

    for doc in documents:
        text_chunks = chunk_text(doc["text"], chunk_size, chunk_overlap)
        filename = Path(doc["path"]).name

        for i, chunk_text_str in enumerate(text_chunks):
            all_chunks.append({
                "chunk_id": _make_chunk_id(doc["domain"], filename, i),
                "text": chunk_text_str,
                "source_file": doc["path"],
                "domain": doc["domain"],
                "token_count": estimate_tokens(chunk_text_str),
            })

        logger.debug(
            "%s → %d chunks", filename, len(text_chunks),
        )

    logger.info(
        "Chunked %d documents into %d chunks (avg %d tokens/chunk)",
        len(documents),
        len(all_chunks),
        int(sum(c["token_count"] for c in all_chunks) / max(len(all_chunks), 1)),
    )
    return all_chunks
