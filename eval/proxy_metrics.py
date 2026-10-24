"""
Proxy Evaluation Script: Measures Document Recall/Precision, Page Recall/Precision,
and Returned vs Gold Chunk Count across benchmark questions (Type A, B, C and Overall).
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

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

def evaluate_retrieval(collection_name: str = "train", split: str = "train", max_questions: int = None) -> Dict[str, Any]:
    benchmark_path = settings.BENCHMARKS_PATH
    if not os.path.exists(benchmark_path):
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    # Load splits
    splits_path = os.path.join(os.path.dirname(__file__), "splits.json")
    with open(splits_path, "r", encoding="utf-8") as f:
        splits = json.load(f)

    if split == "train":
        target_ids = set(splits.get("train_ids", []))
    elif split == "val":
        target_ids = set(splits.get("val_ids", []))
    else:
        target_ids = None

    all_questions = {}
    with open(benchmark_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                all_questions[item["id"]] = item

    if target_ids is not None:
        questions = [all_questions[qid] for qid in splits.get("train_ids" if split == "train" else "val_ids", []) if qid in all_questions]
    else:
        questions = list(all_questions.values())

    if max_questions:
        questions = questions[:max_questions]

    # Metrics storage
    metrics_by_type = defaultdict(lambda: {
        "doc_recalls": [], "doc_precisions": [],
        "page_recalls": [], "page_precisions": [],
        "ret_chunks": [], "gold_chunks": [],
        "latencies": []
    })
    
    overall = {
        "doc_recalls": [], "doc_precisions": [],
        "page_recalls": [], "page_precisions": [],
        "ret_chunks": [], "gold_chunks": [],
        "latencies": [],
        "valid_traces": 0
    }

    col_idx = CollectionIndex(collection_name)
    col_dir = get_collection_dir(collection_name)
    siblings_path = os.path.join(col_dir, "siblings.json")
    sibling_table = {}
    if os.path.exists(siblings_path):
        with open(siblings_path, "r", encoding="utf-8") as f:
            sibling_table = json.load(f)

    print(f"\n================================================================================")
    print(f"RUNNING PROXY RETRIEVAL EVALUATION: Split='{split}' ({len(questions)} questions)")
    print(f"================================================================================\n", flush=True)

    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"Q{i}")
        qtype = qid[0] if qid and qid[0] in ("A", "B", "C") else "Other"
        query_text = q.get("question", "")
        gold_meta = q.get("benchmark_chunks_w_metadata", {})

        gold_docs: Set[str] = set()
        gold_pages: Set[Tuple[str, int]] = set()
        num_gold_chunks = 0

        for doc_name, chunk_list in gold_meta.items():
            norm_doc = normalize_doc_name(doc_name)
            gold_docs.add(norm_doc)
            num_gold_chunks += len(chunk_list)
            for c in chunk_list:
                meta = c.get("metadata", {})
                for p in meta.get("page_numbers", []):
                    gold_pages.add((norm_doc, p))

        t0 = time.time()
        retrieved_chunks, trace, _ = execute_retrieval_pipeline(query_text, col_idx, sibling_table)
        lat = time.time() - t0
        num_ret_chunks = len(retrieved_chunks)

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
            overall["valid_traces"] += 1

        # Check Retrieved docs and pages
        ret_docs: Set[str] = set(c.get("doc_id", c.get("document", "")) for c in retrieved_chunks)
        ret_pages: Set[Tuple[str, int]] = set((c.get("doc_id", c.get("document", "")), c.get("page", 0)) for c in retrieved_chunks)

        # Document Metrics
        if len(gold_docs) > 0:
            doc_rec = len(gold_docs & ret_docs) / len(gold_docs)
        else:
            doc_rec = 1.0

        if len(ret_docs) > 0:
            doc_prec = len(gold_docs & ret_docs) / len(ret_docs)
        else:
            doc_prec = 1.0 if len(gold_docs) == 0 else 0.0

        # Page Metrics
        if len(gold_pages) > 0:
            page_rec = len(gold_pages & ret_pages) / len(gold_pages)
        else:
            page_rec = 1.0

        if len(ret_pages) > 0:
            page_prec = len(gold_pages & ret_pages) / len(ret_pages)
        else:
            page_prec = 1.0 if len(gold_pages) == 0 else 0.0

        # Record by Type
        bucket = metrics_by_type[qtype]
        bucket["doc_recalls"].append(doc_rec)
        bucket["doc_precisions"].append(doc_prec)
        bucket["page_recalls"].append(page_rec)
        bucket["page_precisions"].append(page_prec)
        bucket["ret_chunks"].append(num_ret_chunks)
        bucket["gold_chunks"].append(num_gold_chunks)
        bucket["latencies"].append(lat)

        # Record Overall
        overall["doc_recalls"].append(doc_rec)
        overall["doc_precisions"].append(doc_prec)
        overall["page_recalls"].append(page_rec)
        overall["page_precisions"].append(page_prec)
        overall["ret_chunks"].append(num_ret_chunks)
        overall["gold_chunks"].append(num_gold_chunks)
        overall["latencies"].append(lat)

        if i % 10 == 0 or i == len(questions):
            curr_doc_rec = sum(overall["doc_recalls"]) / len(overall["doc_recalls"])
            curr_page_rec = sum(overall["page_recalls"]) / len(overall["page_recalls"])
            curr_page_prec = sum(overall["page_precisions"]) / len(overall["page_precisions"])
            print(f"[{i:02d}/{len(questions)}] Avg Doc Recall: {curr_doc_rec:.3f} | Avg Page Recall: {curr_page_rec:.3f} | Avg Page Prec: {curr_page_prec:.3f} | Avg Lat: {sum(overall['latencies'])/len(overall['latencies']):.2f}s", flush=True)

    def summarize(data: Dict[str, list]) -> Dict[str, Any]:
        n = len(data["doc_recalls"])
        if n == 0:
            return {}
        return {
            "count": n,
            "doc_recall": round(sum(data["doc_recalls"]) / n, 4),
            "doc_precision": round(sum(data["doc_precisions"]) / n, 4),
            "page_recall": round(sum(data["page_recalls"]) / n, 4),
            "page_precision": round(sum(data["page_precisions"]) / n, 4),
            "avg_ret_chunks": round(sum(data["ret_chunks"]) / n, 1),
            "avg_gold_chunks": round(sum(data["gold_chunks"]) / n, 1),
            "avg_latency_s": round(sum(data["latencies"]) / n, 3),
        }

    summary_by_type = {t: summarize(metrics_by_type[t]) for t in sorted(metrics_by_type.keys())}
    overall_summary = summarize(overall)
    overall_summary["valid_traces_ratio"] = round(overall["valid_traces"] / len(questions), 4)

    print("\n" + "=" * 80)
    print(f"PROXY RETRIEVAL EVALUATION RESULTS (Split: {split}, N={len(questions)})")
    print("=" * 80)
    print(f"{'Type':<8} | {'N':<4} | {'Doc Rec':<9} | {'Doc Prec':<9} | {'Page Rec':<9} | {'Page Prec':<9} | {'Ret Chunks':<11} | {'Gold Chunks':<11}")
    print("-" * 80)
    for t, s in summary_by_type.items():
        print(f"{t:<8} | {s['count']:<4} | {s['doc_recall']:<8.2%} | {s['doc_precision']:<8.2%} | {s['page_recall']:<8.2%} | {s['page_precision']:<8.2%} | {s['avg_ret_chunks']:<11} | {s['avg_gold_chunks']:<11}")
    print("-" * 80)
    print(f"{'OVERALL':<8} | {overall_summary['count']:<4} | {overall_summary['doc_recall']:<8.2%} | {overall_summary['doc_precision']:<8.2%} | {overall_summary['page_recall']:<8.2%} | {overall_summary['page_precision']:<8.2%} | {overall_summary['avg_ret_chunks']:<11} | {overall_summary['avg_gold_chunks']:<11}")
    print(f"Valid Traces Contract: {overall_summary['valid_traces_ratio']:.2%}")
    print(f"Average Pipeline Latency: {overall_summary['avg_latency_s']}s")
    print("=" * 80 + "\n", flush=True)

    return {
        "overall": overall_summary,
        "by_type": summary_by_type
    }

if __name__ == "__main__":
    split_name = "train"
    max_q = None
    for arg in sys.argv[1:]:
        if arg in ("train", "val", "all"):
            split_name = arg
        elif arg.isdigit():
            max_q = int(arg)
    
    evaluate_retrieval("train", split=split_name, max_questions=max_q)
