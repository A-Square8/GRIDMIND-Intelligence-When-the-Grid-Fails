import time
import json
import resource
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gridmind.eval")


def get_python_ram_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def get_ollama_ram_mb():
    try:
        out = subprocess.check_output(
            "ps -eo rss,comm | grep -i ollama | awk '{sum+=$1} END {print sum}'",
            shell=True,
        )
        kb = out.decode().strip()
        if kb:
            return float(kb) / 1024.0
    except Exception:
        pass
    return 0.0


def eval_retrieval(retriever):
    print("\n--- Retrieval Benchmarks ---")

    queries = [
        ("how to purify water from a river", "03_water"),
        ("building a temporary shelter", "01_survival"),
        ("treating a deep wound", "02_health"),
        ("how to find food in the wild", "01_survival"),
        ("how to fix a broken bone", "02_health"),
    ]

    retrieval_times = []
    correct_domain = 0
    mrr_sum = 0.0
    total_queries = len(queries)
    results_log = []

    for q, expected_domain in queries:
        t0 = time.time()
        res = retriever.retrieve(q, top_k=5)
        retrieval_times.append(time.time() - t0)

        domains = [r["domain"] for r in res]
        found = expected_domain in domains

        rr = 0.0
        for rank, d in enumerate(domains, 1):
            if d == expected_domain:
                rr = 1.0 / rank
                break

        mrr_sum += rr

        if found:
            correct_domain += 1

        status = "PASS" if found else "FAIL"
        print(f"  [{status}] '{q}' -> domains: {domains} (RR: {rr:.2f})")
        results_log.append({
            "query": q,
            "expected": expected_domain,
            "found_domains": domains,
            "status": status,
            "rr": rr,
        })

    avg_retrieval = sum(retrieval_times) / len(retrieval_times)
    precision = (correct_domain / total_queries) * 100
    mrr = mrr_sum / total_queries

    print(f"\n  Avg Retrieval Latency: {avg_retrieval:.3f}s")
    print(f"  Precision (Domain in Top-5): {precision:.1f}%")
    print(f"  MRR (Mean Reciprocal Rank): {mrr:.3f}")

    return {
        "avg_latency": round(avg_retrieval, 3),
        "precision": round(precision, 1),
        "mrr": round(mrr, 3),
        "results": results_log,
    }


def eval_relevance_gate(retriever, gate):
    print("\n--- Relevance Gate Benchmarks ---")

    in_domain = [
        "how to purify water",
        "treating a burn wound",
        "building a shelter in winter",
    ]

    out_domain = [
        "how to invest in stocks",
        "best programming language to learn",
        "recipe for chocolate cake",
        "how to fix a SQL injection vulnerability",
    ]

    gate_results = {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}

    for q in in_domain:
        chunks = retriever.retrieve(q, top_k=3)
        distances = retriever.get_raw_distances(q, top_k=3)
        result = gate.evaluate(q, chunks, distances)
        expected_pass = result == "PASS"
        if expected_pass:
            gate_results["true_positive"] += 1
            print(f"  [PASS] In-domain: '{q}' -> {result}")
        else:
            gate_results["false_negative"] += 1
            print(f"  [FAIL] In-domain: '{q}' -> {result} (expected PASS)")

    for q in out_domain:
        chunks = retriever.retrieve(q, top_k=3)
        distances = retriever.get_raw_distances(q, top_k=3)
        result = gate.evaluate(q, chunks, distances)
        expected_reject = result in ("NO_MATCH", "LOW_CONFIDENCE")
        if expected_reject:
            gate_results["true_negative"] += 1
            print(f"  [PASS] Out-domain: '{q}' -> {result}")
        else:
            gate_results["false_positive"] += 1
            print(f"  [FAIL] Out-domain: '{q}' -> {result} (expected NO_MATCH/LOW_CONFIDENCE)")

    total = sum(gate_results.values())
    accuracy = (gate_results["true_positive"] + gate_results["true_negative"]) / total * 100

    print(f"\n  Gate Accuracy: {accuracy:.1f}%")
    print(f"  True Positives: {gate_results['true_positive']}")
    print(f"  True Negatives: {gate_results['true_negative']}")
    print(f"  False Positives: {gate_results['false_positive']}")
    print(f"  False Negatives: {gate_results['false_negative']}")

    return {**gate_results, "accuracy": round(accuracy, 1)}


def eval_procedure_matching(retriever):
    print("\n--- Procedure Matching Benchmarks ---")

    if not retriever.procedures:
        print("  No procedures extracted. Skipping.")
        return {"status": "skipped", "total_procedures": 0}

    test_queries = [
        "how to purify water",
        "building a fire",
        "treating a wound",
        "building shelter",
        "finding food",
    ]

    total_matches = 0
    for q in test_queries:
        procs = retriever.match_procedures(q)
        total_matches += len(procs)
        if procs:
            titles = [p.get("title", "N/A") for p in procs]
            print(f"  '{q}' -> {len(procs)} procedures: {titles}")
        else:
            print(f"  '{q}' -> no procedures matched")

    print(f"\n  Total procedures in index: {len(retriever.procedures)}")
    print(f"  Total matches across test queries: {total_matches}")

    return {
        "total_procedures": len(retriever.procedures),
        "total_matches": total_matches,
    }


def eval_e2e(pipeline, retriever):
    print("\n--- E2E Pipeline Benchmarks ---")

    query_text = "What are the most important steps to purify river water?"
    print(f"  Testing: '{query_text}'")

    t0 = time.time()
    response = ""
    ttft = 0.0

    for i, chunk in enumerate(pipeline.query(query_text, top_k=3)):
        if i == 0:
            ttft = time.time() - t0
        response += chunk

    gen_time = time.time() - t0

    has_do_this = "**Do this" in response or "**1." in response
    has_hard_stops = "Hard stop" in response.lower() or "hard stop" in response.lower()
    has_sys_complete = "[SYS] Output complete" in response

    print(f"  Response length: {len(response)} chars")
    print(f"  TTFT: {ttft:.2f}s")
    print(f"  Total latency: {gen_time:.2f}s")
    print(f"  Has 'Do this' section: {has_do_this}")
    print(f"  Has 'Hard stops' section: {has_hard_stops}")
    print(f"  Has termination marker: {has_sys_complete}")

    return {
        "response_length": len(response),
        "ttft": round(ttft, 2),
        "total_latency": round(gen_time, 2),
        "format_compliance": {
            "do_this": has_do_this,
            "hard_stops": has_hard_stops,
            "sys_complete": has_sys_complete,
        },
    }


def generate_report(retrieval, gate, procedures, e2e, memory):
    report_path = Path("data/eval_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# GridMind V2 Evaluation Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Retrieval Quality",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Avg Latency | {retrieval['avg_latency']}s |",
        f"| Precision (Top-5) | {retrieval['precision']}% |",
        f"| MRR | {retrieval['mrr']} |",
        "",
        "## Relevance Gate",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {gate['accuracy']}% |",
        f"| True Positives | {gate['true_positive']} |",
        f"| True Negatives | {gate['true_negative']} |",
        f"| False Positives | {gate['false_positive']} |",
        f"| False Negatives | {gate['false_negative']} |",
        "",
        "## Procedure Matching",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Procedures | {procedures.get('total_procedures', 0)} |",
        f"| Test Matches | {procedures.get('total_matches', 0)} |",
        "",
        "## E2E Pipeline",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Response Length | {e2e['response_length']} chars |",
        f"| TTFT | {e2e['ttft']}s |",
        f"| Total Latency | {e2e['total_latency']}s |",
        "",
        "## Memory Usage",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Peak Python RAM | {memory['peak_python']} MB |",
        f"| Peak Ollama RAM | {memory['peak_ollama']} MB |",
        f"| Total Footprint | {memory['total']} MB |",
        "",
    ]

    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\nReport saved to {report_path}")


def main():
    from core.retriever import ContextRetriever
    from core.rag_pipeline import RAGPipeline
    from core.llm_engine import create_llm_backend
    from core.relevance_gate import RelevanceGate

    print("=" * 50)
    print("GridMind V2 Evaluation Suite")
    print("=" * 50)

    base_py_ram = get_python_ram_mb()
    base_ollama_ram = get_ollama_ram_mb()
    print(f"Base Python RAM: {base_py_ram:.1f} MB")
    print(f"Base Ollama RAM: {base_ollama_ram:.1f} MB")

    t0 = time.time()
    retriever = ContextRetriever()
    init_time = time.time() - t0
    print(f"Retriever init: {init_time:.2f}s")

    gate = RelevanceGate()

    retrieval_results = eval_retrieval(retriever)
    gate_results = eval_relevance_gate(retriever, gate)
    procedure_results = eval_procedure_matching(retriever)

    print("\nInitializing LLM for E2E test...")
    llm = create_llm_backend()
    pipeline = RAGPipeline(llm, retriever)

    e2e_results = eval_e2e(pipeline, retriever)

    peak_py = get_python_ram_mb()
    peak_ollama = get_ollama_ram_mb()
    memory_results = {
        "peak_python": round(peak_py, 1),
        "peak_ollama": round(peak_ollama, 1),
        "total": round(peak_py + peak_ollama, 1),
    }

    print(f"\n--- Memory Usage ---")
    print(f"  Peak Python: {peak_py:.1f} MB (delta: +{peak_py - base_py_ram:.1f} MB)")
    print(f"  Peak Ollama: {peak_ollama:.1f} MB")
    print(f"  Total: {peak_py + peak_ollama:.1f} MB")

    generate_report(retrieval_results, gate_results, procedure_results, e2e_results, memory_results)

    print("\n" + "=" * 50)
    print("Evaluation complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()
