#!/usr/bin/env python3

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


def run_llm_test(args):
    from core.llm_engine import create_llm_backend

    kwargs = {}
    if args.backend == "ollama":
        if args.model:
            kwargs["model"] = args.model
    elif args.backend == "llama_cpp":
        if not args.model:
            print("ERROR: --model <path-to-gguf> is required for llama_cpp backend")
            sys.exit(1)
        kwargs["model_path"] = args.model

    llm = create_llm_backend(args.backend, **kwargs)

    print("=" * 60)
    print(f"Backend : {args.backend}")
    print(f"Model   : {args.model or '(default)'}")
    print("=" * 60)
    print("Running health check ...", end=" ", flush=True)
    if llm.health_check():
        print("OK")
    else:
        print("FAILED")
        sys.exit(1)

    print()
    print(f"Prompt: {SMOKE_PROMPT}")
    print("-" * 60)

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
    print("-" * 60)
    print(f"Total time: {elapsed:.1f}s")


def run_ingest_test(args):
    from ingestion.loader import load_documents
    from ingestion.chunker import chunk_documents

    base_dir = Path(args.docs_dir) if args.docs_dir else RAW_DOCS_DIR

    print("=" * 60)
    print(f"Ingestion test -- source: {base_dir}")
    print("=" * 60)

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
        print(f"  [{doc['domain']}] {name} -- {chars:,} chars")

    t1 = time.perf_counter()
    chunks = chunk_documents(documents)
    chunk_time = time.perf_counter() - t1

    print(f"\nChunked into {len(chunks)} chunks in {chunk_time:.1f}s")
    token_counts = [c["token_count"] for c in chunks]
    print(f"  Token range: {min(token_counts)}-{max(token_counts)}")
    print(f"  Avg tokens:  {sum(token_counts) // len(token_counts)}")

    sample = chunks[len(chunks) // 2]
    print("\n--- Sample Chunk ---")
    print(f"  chunk_id:    {sample['chunk_id']}")
    print(f"  domain:      {sample['domain']}")
    print(f"  source_file: {Path(sample['source_file']).name}")
    print(f"  token_count: {sample['token_count']}")
    print(f"  text[:300]:  {sample['text'][:300]}...")
    print("-" * 60)
    print(f"Total time: {load_time + chunk_time:.1f}s")


def run_index_test(args):
    from ingestion.loader import load_documents
    from ingestion.chunker import chunk_documents
    from ingestion.indexer import build_index, incremental_index
    from core.embeddings import OllamaEmbedder

    base_dir = Path(args.docs_dir) if args.docs_dir else RAW_DOCS_DIR
    store_dir = Path(args.store_dir) if args.store_dir else None

    print("=" * 60)
    print(f"Index build -- source: {base_dir}")
    print("=" * 60)

    embedder = OllamaEmbedder(model=args.model or "nomic-embed-text")

    if getattr(args, "incremental", False):
        print("Running in INCREMENTAL mode (hashing files...)")
        t0 = time.perf_counter()
        index, metadata = incremental_index(
            base_dir, embedder, batch_size=args.batch_size, store_dir=store_dir
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
            chunks, embedder, batch_size=args.batch_size, output_dir=store_dir
        )
        total_time = time.perf_counter() - t0

    store = Path(store_dir or "data/vector_store")
    idx_size = (store / "index.faiss").stat().st_size
    meta_size = (store / "metadata.json").stat().st_size

    print(f"\n{'=' * 60}")
    print(f"Vectors:       {index.ntotal}")
    print(f"Dimensions:    {index.d}")
    print(f"Index size:    {idx_size / 1e6:.1f} MB")
    print(f"Metadata size: {meta_size / 1e6:.1f} MB")
    print(f"Total time:    {total_time:.1f}s")
    print("=" * 60)


def run_retrieve_test(args):
    from core.retriever import ContextRetriever

    print("=" * 60)
    print(f"Retrieval Test -- Query: '{args.query}'")
    print("=" * 60)

    retriever = ContextRetriever(store_dir=args.store_dir)
    results = retriever.retrieve(args.query, top_k=args.top_k, domain_filter=args.domain)

    if not results:
        print("No matches found.")
        return

    for i, res in enumerate(results, 1):
        print(f"[{i}] Score: {res['score']:.4f} | Domain: {res['domain']}")
        print(f"    Source: {res['source_file']}")
        print(f"    Text: {res['text'][:300]}...\n")

    procedures = retriever.match_procedures(args.query)
    if procedures:
        print(f"\n--- Matched {len(procedures)} Procedures ---")
        for proc in procedures:
            print(f"  Title: {proc.get('title', 'N/A')}")
            print(f"  Steps: {len(proc.get('steps', []))}")
            print()


def run_ask_test(args):
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

    print("\n" + "=" * 60)
    print(f"GridMind Query: {args.query}")
    print("=" * 60)

    for chunk in pipeline.query(args.query, top_k=args.top_k, domain_filter=args.domain):
        print(chunk, end="", flush=True)
    print("\n" + "=" * 60)


def run_extract_procedures(args):
    from core.llm_engine import create_llm_backend
    from ingestion.procedure_extractor import extract_procedures_from_chunks, save_procedures
    import json

    store = Path(args.store_dir or "data/vector_store")
    metadata_path = store / "metadata.json"

    if not metadata_path.exists():
        print("No metadata.json found. Run 'index' first.")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Extracting procedures from {len(metadata)} chunks...")
    print("This will take a while (1 LLM call per chunk).")

    llm = create_llm_backend(backend="ollama")
    procedures = extract_procedures_from_chunks(metadata, llm, batch_delay=0.3)

    output_path = store / "procedures.json"
    save_procedures(procedures, output_path)

    print(f"\nExtracted {len(procedures)} procedures.")
    for proc in procedures[:5]:
        print(f"  - {proc.get('title', 'N/A')} ({len(proc.get('steps', []))} steps)")


def run_extract_concepts(args):
    from core.llm_engine import create_llm_backend
    from ingestion.concept_extractor import extract_concepts_from_chunks, save_concepts
    import json

    store = Path(args.store_dir or "data/vector_store")
    metadata_path = store / "metadata.json"

    if not metadata_path.exists():
        print("No metadata.json found. Run 'index' first.")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Extracting concepts from {len(metadata)} chunks...")
    print("This will take a while (1 LLM call per chunk).")

    llm = create_llm_backend(backend="ollama")
    concepts = extract_concepts_from_chunks(metadata, llm, batch_delay=0.3)

    output_path = store / "concepts.json"
    save_concepts(concepts, output_path)

    print(f"\nExtracted {len(concepts)} concepts.")
    for name in list(concepts.keys())[:10]:
        data = concepts[name]
        print(f"  - {name}")
        if data.get("requires"):
            print(f"    requires: {', '.join(data['requires'][:5])}")
        if data.get("related"):
            print(f"    related: {', '.join(data['related'][:5])}")


def main():
    parser = argparse.ArgumentParser(description="GridMind CLI")

    sub = parser.add_subparsers(dest="command")

    llm_p = sub.add_parser("llm", help="LLM inference test")
    llm_p.add_argument("--backend", choices=["ollama", "llama_cpp"], default="ollama")
    llm_p.add_argument("--model", default=None)
    llm_p.add_argument("--no-stream", action="store_true")

    ingest_p = sub.add_parser("ingest", help="Document ingestion test")
    ingest_p.add_argument("--docs-dir", default=None)

    index_p = sub.add_parser("index", help="Build FAISS + BM25 index")
    index_p.add_argument("--docs-dir", default=None)
    index_p.add_argument("--store-dir", default=None)
    index_p.add_argument("--model", default=None)
    index_p.add_argument("--batch-size", type=int, default=8)
    index_p.add_argument("--incremental", action="store_true")

    retrieve_p = sub.add_parser("retrieve", help="Test retrieval system")
    retrieve_p.add_argument("query", type=str)
    retrieve_p.add_argument("--top-k", type=int, default=3)
    retrieve_p.add_argument("--domain", default=None)
    retrieve_p.add_argument("--store-dir", default=None)

    ask_p = sub.add_parser("ask", help="Test end-to-end RAG pipeline")
    ask_p.add_argument("query", type=str)
    ask_p.add_argument("--llm", choices=["ollama", "llamacpp"], default="ollama")
    ask_p.add_argument("--model-path", default=None)
    ask_p.add_argument("--top-k", type=int, default=3)
    ask_p.add_argument("--domain", default=None)
    ask_p.add_argument("--store-dir", default=None)

    proc_p = sub.add_parser("extract-procedures", help="Extract procedures from indexed chunks")
    proc_p.add_argument("--store-dir", default=None)

    concept_p = sub.add_parser("extract-concepts", help="Extract concept graph from indexed chunks")
    concept_p.add_argument("--store-dir", default=None)

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
    elif args.command == "extract-procedures":
        run_extract_procedures(args)
    elif args.command == "extract-concepts":
        run_extract_concepts(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
