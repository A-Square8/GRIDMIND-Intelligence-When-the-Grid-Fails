import time
import os
import resource
import subprocess
from core.retriever import ContextRetriever
from core.rag_pipeline import RAGPipeline
from core.llm_engine import create_llm_backend

def get_python_ram_mb():

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def get_ollama_ram_mb():
    try:
        out = subprocess.check_output("ps -eo rss,comm | grep -i ollama | awk '{sum+=$1} END {print sum}'", shell=True)
        kb = out.decode().strip()
        if kb:
            return float(kb) / 1024.0
    except Exception:
        pass
    return 0.0

def main():
    print(f"--- GridMind Evaluation & Benchmarks ---")
    base_py_ram = get_python_ram_mb()
    base_ollama_ram = get_ollama_ram_mb()
    print(f"Base Python RAM: {base_py_ram:.1f} MB")
    print(f"Base Ollama RAM: {base_ollama_ram:.1f} MB")
    print("-" * 40)
    
    t0 = time.time()
    retriever = ContextRetriever()
    init_time = time.time() - t0
    print(f"Retriever Init Time: {init_time:.2f}s")
    
    # Evaluate Retrieval Precision
    queries = [
        ("how to purify water from a river", "03_water"),
        ("building a temporary shelter", "01_survival"),
        ("treating a deep wound", "02_health"),
        ("how to find food in the wild", "01_survival"),
        ("how to fix a broken bone", "02_health")
    ]
    
    retrieval_times = []
    correct_domain = 0
    total_queries = len(queries)
    
    print("\n--- Retrieval Benchmarks ---")
    for q, expected_domain in queries:
        t0 = time.time()
        res = retriever.retrieve(q, top_k=3)
        retrieval_times.append(time.time() - t0)
        
        domains = [r["domain"] for r in res]
        if expected_domain in domains:
            correct_domain += 1
            print(f"Query: '{q}' -> SUCCESS (Found in {domains})")
        else:
            print(f"Query: '{q}' -> FAIL (Found in {domains})")
            
    avg_retrieval_time = sum(retrieval_times)/len(retrieval_times)
    precision = (correct_domain / total_queries) * 100
    
    print(f"Average Retrieval Latency: {avg_retrieval_time:.3f} seconds")
    print(f"Retrieval Precision (Domain Match in Top-3): {precision:.1f}%")
    
    print("\n--- E2E Pipeline Benchmarks ---")
    llm = create_llm_backend()
    pipeline = RAGPipeline(llm, retriever)
    
    t0 = time.time()
    query_text = "What are the most important steps to purify river water?"
    print(f"Testing Answer Latency on: '{query_text}'")
    
    response = ""

    ttft = 0.0
    for i, chunk in enumerate(pipeline.query(query_text, top_k=3)):
        if i == 0:
            ttft = time.time() - t0
        response += chunk
        
    gen_time = time.time() - t0
    
    print(f"\nResponse length: {len(response)} characters")
    print(f"Time to First Token (TTFT): {ttft:.2f} seconds")
    print(f"Total Generation Latency: {gen_time:.2f} seconds")
    
    print("\n--- Memory Usage (Peak) ---")
    peak_py_ram = get_python_ram_mb()
    peak_ollama_ram = get_ollama_ram_mb()
    print(f"Peak Python RAM: {peak_py_ram:.1f} MB (Delta: +{peak_py_ram - base_py_ram:.1f} MB)")
    print(f"Peak Ollama RAM: {peak_ollama_ram:.1f} MB (Delta: +{peak_ollama_ram - base_ollama_ram:.1f} MB)")
    print(f"Total System Footprint: {peak_py_ram + peak_ollama_ram:.1f} MB")
    print("-" * 40)
    
if __name__ == '__main__':
    main()
