"""
Proxy Evaluation Script: Measures Document Recall/Precision, Page Recall/Precision,
and validates execution trace across the 100 benchmark questions.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List, Set, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from ingest.index_build import CollectionIndex, get_collection_dir
from retrieve.assemble import execute_retrieval_pipeline

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("proxy_eval")

# Mapping of missing/renamed benchmark document names to train corpus equivalents
DOC_NAME_EQUIVALENTS = {
    "Guidelines on Management of Problem Loans.pdf": "SAMA_EN_3575_VER1.pdf",
    "2026-05960.pdf": "91fr14908.pdf",
    "fact-sheet-20260319.pdf": "fact-sheet-SUMMARY.pdf",
}

def normalize_doc_name(name: str) -> str:
    return DOC_NAME_EQUIVALENTS.get(name, name)

def evaluate_retrieval(collection_name: str = "train", max_questions: int = 100) -> Dict[str, Any]:
    benchmark_path = settings.BENCHMARKS_PATH
    if not os.path.exists(benchmark_path):
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    questions = []
    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))

    if max_questions:
        questions = questions[:max_questions]

    doc_recalls = []
    doc_precisions = []
    page_recalls = []
    page_precisions = []
    chunk_counts = []
    latencies = []
    valid_traces = 0

    col_idx = CollectionIndex(collection_name)
    col_dir = get_collection_dir(collection_name)
    siblings_path = os.path.join(col_dir, "siblings.json")
    sibling_table = {}
    if os.path.exists(siblings_path):
        with open(siblings_path, "r", encoding="utf-8") as f:
            sibling_table = json.load(f)

    print(f"Running proxy retrieval evaluation on {len(questions)} questions from benchmark...")

    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"Q{i}")
        query_text = q.get("question", "")
        gold_meta = q.get("benchmark_chunks_w_metadata", {})

        gold_docs: Set[str] = set()
        gold_pages: Set[Tuple[str, int]] = set()

        for doc_name, chunk_list in gold_meta.items():
            norm_doc = normalize_doc_name(doc_name)
            gold_docs.add(norm_doc)
            for c in chunk_list:
                meta = c.get("metadata", {})
                for p in meta.get("page_numbers", []):
                    gold_pages.add((norm_doc, p))

        t0 = time.time()
        retrieved_chunks, trace, _ = execute_retrieval_pipeline(query_text, col_idx, sibling_table)
        lat = time.time() - t0
        latencies.append(lat)
        chunk_counts.append(len(retrieved_chunks))

        # Check trace contract
        has_valid_trace = (
            isinstance(trace, list)
            and len(trace) >= 7
            and all(
                all(k in step for k in ["step_name", "description", "input", "output"])
                for step in trace
            )
        )
        if has_valid_trace:
            valid_traces += 1

        # Check Retrieved docs and pages
        ret_docs: Set[str] = set(c.get("doc_id", c.get("document", "")) for c in retrieved_chunks)
        ret_pages: Set[Tuple[str, int]] = set((c.get("doc_id", c.get("document", "")), c.get("page", 0)) for c in retrieved_chunks)

        # Document Metrics
        if len(gold_docs) > 0:
            doc_rec = len(gold_docs & ret_docs) / len(gold_docs)
            doc_recalls.append(doc_rec)
        else:
            doc_recalls.append(1.0 if len(ret_docs) == 0 else 1.0)

        if len(ret_docs) > 0:
            doc_prec = len(gold_docs & ret_docs) / len(ret_docs)
            doc_precisions.append(doc_prec)
        else:
            doc_precisions.append(1.0 if len(gold_docs) == 0 else 0.0)

        # Page Metrics
        if len(gold_pages) > 0:
            page_rec = len(gold_pages & ret_pages) / len(gold_pages)
            page_recalls.append(page_rec)
        else:
            page_recalls.append(1.0 if len(ret_pages) == 0 else 1.0)

        if len(ret_pages) > 0:
            page_prec = len(gold_pages & ret_pages) / len(ret_pages)
            page_precisions.append(page_prec)
        else:
            page_precisions.append(1.0 if len(gold_pages) == 0 else 0.0)

        if i % 10 == 0 or i == len(questions):
            curr_doc_rec = sum(doc_recalls) / len(doc_recalls)
            curr_page_rec = sum(page_recalls) / len(page_recalls)
            print(f"[{i}/{len(questions)}] Avg Doc Recall: {curr_doc_rec:.3f} | Avg Page Recall: {curr_page_rec:.3f} | Avg Latency: {sum(latencies)/len(latencies):.2f}s")

    avg_doc_recall = sum(doc_recalls) / len(doc_recalls) if doc_recalls else 0.0
    avg_doc_prec = sum(doc_precisions) / len(doc_precisions) if doc_precisions else 0.0
    avg_page_recall = sum(page_recalls) / len(page_recalls) if page_recalls else 0.0
    avg_page_prec = sum(page_precisions) / len(page_precisions) if page_precisions else 0.0
    avg_chunks = sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0.0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    results = {
        "questions_evaluated": len(questions),
        "document_recall": round(avg_doc_recall, 4),
        "document_precision": round(avg_doc_prec, 4),
        "page_recall": round(avg_page_recall, 4),
        "page_precision": round(avg_page_prec, 4),
        "avg_retrieved_chunks": round(avg_chunks, 1),
        "avg_latency_s": round(avg_lat, 3),
        "valid_traces_ratio": round(valid_traces / len(questions), 4),
    }

    print("\n" + "=" * 60)
    print("PROXY EVALUATION RESULTS")
    print(f"Questions Evaluated:    {results['questions_evaluated']}")
    print(f"Document Recall:        {results['document_recall']:.2%}")
    print(f"Document Precision:     {results['document_precision']:.2%}")
    print(f"Page Recall:            {results['page_recall']:.2%}")
    print(f"Page Precision:         {results['page_precision']:.2%}")
    print(f"Avg Retrieved Chunks:   {results['avg_retrieved_chunks']}")
    print(f"Avg Pipeline Latency:   {results['avg_latency_s']}s")
    print(f"Valid Traces Contract:  {results['valid_traces_ratio']:.2%}")
    print("=" * 60 + "\n")

    return results

if __name__ == "__main__":
    n_q = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    evaluate_retrieval("train", max_questions=n_q)
