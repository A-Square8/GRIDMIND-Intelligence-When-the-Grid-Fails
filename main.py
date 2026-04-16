#!/usr/bin/env python3
"""
GridMind — Smoke Tests
Stage 1: LLM inference test
Stage 2: Document ingestion test
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("gridmind")

SMOKE_PROMPT = (
    "What are the three most important things to do "
    "if you are lost in the wilderness?"
)

RAW_DOCS_DIR = Path(__file__).parent / "raw_docs"


# ---------------------------------------------------------------------------
# Stage 1: LLM smoke test
# ---------------------------------------------------------------------------

def run_llm_test(args: argparse.Namespace) -> None:
    from core.llm_engine import create_llm_backend

    kwargs: dict = {}
    if args.backend == "ollama":
        if args.model:
            kwargs["model"] = args.model
    elif args.backend == "llama_cpp":
        if not args.model:
            print("ERROR: --model <path-to-gguf> is required for llama_cpp backend")
            sys.exit(1)
        kwargs["model_path"] = args.model

    llm = create_llm_backend(args.backend, **kwargs)

    print("━" * 60)
    print(f"Backend : {args.backend}")
    print(f"Model   : {args.model or '(default)'}")
    print("━" * 60)
    print("Running health check …", end=" ", flush=True)
    if llm.health_check():
        print("✓ OK")
    else:
        print("✗ FAILED")
        sys.exit(1)

    print()
    print(f"Prompt: {SMOKE_PROMPT}")
    print("─" * 60)

    t0 = time.perf_counter()
    stream = not args.no_stream
    result = llm.generate(SMOKE_PROMPT, stream=stream)

    if isinstance(result, Generator) or hasattr(result, "__next__"):
        for chunk in result:
            print(chunk, end="", flush=True)
        print()
    else:
        print(result)

    elapsed = time.perf_counter() - t0
    print("─" * 60)
    print(f"Total time: {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Stage 2: Ingestion smoke test
# ---------------------------------------------------------------------------

def run_ingest_test(args: argparse.Namespace) -> None:
    from ingestion.loader import load_documents
    from ingestion.chunker import chunk_documents

    base_dir = Path(args.docs_dir) if args.docs_dir else RAW_DOCS_DIR

    print("━" * 60)
    print(f"Ingestion test — source: {base_dir}")
    print("━" * 60)

    # Load documents
    t0 = time.perf_counter()
    documents = load_documents(base_dir)
    load_time = time.perf_counter() - t0

    if not documents:
        print("No documents found!")
        sys.exit(1)

    print(f"\nLoaded {len(documents)} documents in {load_time:.1f}s")
    for doc in documents:
        name = Path(doc["path"]).name
        chars = len(doc["text"])
        print(f"  [{doc['domain']}] {name} — {chars:,} chars")

    # Chunk documents
    t1 = time.perf_counter()
    chunks = chunk_documents(documents)
    chunk_time = time.perf_counter() - t1

    print(f"\nChunked into {len(chunks)} chunks in {chunk_time:.1f}s")
    token_counts = [c["token_count"] for c in chunks]
    print(f"  Token range: {min(token_counts)}–{max(token_counts)}")
    print(f"  Avg tokens:  {sum(token_counts) // len(token_counts)}")

    # Show a sample chunk
    sample = chunks[len(chunks) // 2]  # pick one from the middle
    print("\n─── Sample Chunk ───────────────────────────────────────────")
    print(f"  chunk_id:    {sample['chunk_id']}")
    print(f"  domain:      {sample['domain']}")
    print(f"  source_file: {Path(sample['source_file']).name}")
    print(f"  token_count: {sample['token_count']}")
    print(f"  text[:300]:  {sample['text'][:300]}…")
    print("─" * 60)
    print(f"Total time: {load_time + chunk_time:.1f}s")


def run_index_test(args: argparse.Namespace) -> None:
    from ingestion.loader import load_documents
    from ingestion.chunker import chunk_documents
    from ingestion.indexer import build_index, incremental_index
    from core.embeddings import OllamaEmbedder

    base_dir = Path(args.docs_dir) if args.docs_dir else RAW_DOCS_DIR
    store_dir = Path(args.store_dir) if args.store_dir else None

    print("━" * 60)
    print(f"Index build — source: {base_dir}")
    print("━" * 60)

    embedder = OllamaEmbedder(model=args.model or "nomic-embed-text")

    if getattr(args, "incremental", False):
        print("Running in FULL INCEMENTAL mode (hashing files...)")
        t0 = time.perf_counter()
        index, metadata = incremental_index(
            base_dir, embedder,
            batch_size=args.batch_size,
            store_dir=store_dir,
        )
        total_time = time.perf_counter() - t0
        if index is None:
            print("\nNo vectors generated.")
            return
    else:
        documents = load_documents(base_dir)
        if not documents:
            print("No documents found!")
            sys.exit(1)

        chunks = chunk_documents(documents)
        print(f"\n{len(chunks)} chunks ready for embedding")

        t0 = time.perf_counter()
        index, metadata = build_index(
            chunks, embedder,
            batch_size=args.batch_size,
            output_dir=store_dir,
        )
        total_time = time.perf_counter() - t0

    store = Path(store_dir or "data/vector_store")
    idx_size = (store / "index.faiss").stat().st_size
    meta_size = (store / "metadata.json").stat().st_size

    print(f"\n{'━' * 60}")
    print(f"Vectors:       {index.ntotal}")
    print(f"Dimensions:    {index.d}")
    print(f"Index size:    {idx_size / 1e6:.1f} MB")
    print(f"Metadata size: {meta_size / 1e6:.1f} MB")
    print(f"Total time:    {total_time:.1f}s")
    print("━" * 60)


def run_retrieve_test(args: argparse.Namespace) -> None:
    from core.retriever import ContextRetriever
    print("━" * 60)
    print(f"Retrieval Test — Query: '{args.query}'")
    print("━" * 60)
    
    retriever = ContextRetriever(store_dir=args.store_dir)
    results = retriever.retrieve(args.query, top_k=args.top_k, domain_filter=args.domain)
    
    if not results:
        print("No matches found.")
        return
        
    for i, res in enumerate(results, 1):
        print(f"[{i}] Score: {res['score']:.4f} | Domain: {res['domain']}")
        print(f"    Source: {res['source_file']}")
        print(f"    Text: {res['text'][:300]}...\n")


def run_ask_test(args: argparse.Namespace) -> None:
    from core.llm_engine import create_llm_backend
    from core.retriever import ContextRetriever
    from core.rag_pipeline import RAGPipeline

    print(f"Loading LLM ({args.llm})...")
    if args.llm == "llamacpp":
        llm = create_llm_backend(backend=args.llm, model_path=args.model_path)
    else:
        llm = create_llm_backend(backend=args.llm)
    
    print("Loading Index...")
    retriever = ContextRetriever(store_dir=args.store_dir)
    pipeline = RAGPipeline(llm=llm, retriever=retriever)
    
    print("\n" + "━" * 60)
    print(f"GridMind Query: {args.query}")
    print("━" * 60)
    
    for chunk in pipeline.query(args.query, top_k=args.top_k, domain_filter=args.domain):
        print(chunk, end="", flush=True)
    print("\n" + "━" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="GridMind smoke tests")

    sub = parser.add_subparsers(dest="command")

    # Stage 1: llm
    llm_p = sub.add_parser("llm", help="Stage 1 — LLM inference test")
    llm_p.add_argument(
        "--backend", choices=["ollama", "llama_cpp"], default="ollama",
    )
    llm_p.add_argument("--model", default=None)
    llm_p.add_argument("--no-stream", action="store_true")

    # Stage 2: ingest
    ingest_p = sub.add_parser("ingest", help="Stage 2 — Document ingestion test")
    ingest_p.add_argument(
        "--docs-dir", default=None,
        help=f"Path to raw docs directory (default: {RAW_DOCS_DIR})",
    )

    index_p = sub.add_parser("index", help="Stage 3 — Build FAISS index")
    index_p.add_argument("--docs-dir", default=None)
    index_p.add_argument("--store-dir", default=None)
    index_p.add_argument("--model", default=None)
    index_p.add_argument("--batch-size", type=int, default=32)
    index_p.add_argument("--incremental", action="store_true", help="Perform incremental append using file hashing")

    retrieve_p = sub.add_parser("retrieve", help="Stage 4 — Test retrieval system")
    retrieve_p.add_argument("query", type=str)
    retrieve_p.add_argument("--top-k", type=int, default=3)
    retrieve_p.add_argument("--domain", default=None)
    retrieve_p.add_argument("--store-dir", default=None)

    ask_p = sub.add_parser("ask", help="Stage 5 — Test end-to-end RAG pipeline")
    ask_p.add_argument("query", type=str)
    ask_p.add_argument("--llm", choices=["ollama", "llamacpp"], default="ollama")
    ask_p.add_argument("--model-path", default=None)
    ask_p.add_argument("--top-k", type=int, default=3)
    ask_p.add_argument("--domain", default=None)
    ask_p.add_argument("--store-dir", default=None)

    args = parser.parse_args()

    if args.command == "llm":
        run_llm_test(args)
    elif args.command == "ingest":
        run_ingest_test(args)
    elif args.command == "index":
        run_index_test(args)
    elif args.command == "retrieve":
        run_retrieve_test(args)
    elif args.command == "ask":
        run_ask_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
