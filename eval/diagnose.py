"""
Evaluation Diagnostic & Failure Analysis Tool.
Triages questions with Answer Precision/Recall < 0.95 or Context Precision/Recall < 0.95
into actionable root cause failure classes.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def diagnose_evaluation_results(results_file: str):
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        return

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("per_question", [])
    print("\n" + "=" * 70)
    print(f"DIAGNOSTIC REPORT: {data.get('split', 'unknown').upper()} SET ({len(questions)} Questions)")
    print(f"Average Answer Precision:  {data.get('avg_answer_precision', 0):.2%}")
    print(f"Average Answer Recall:     {data.get('avg_answer_recall', 0):.2%}")
    print(f"Average Context Precision: {data.get('avg_context_precision', 0):.2%}")
    print(f"Average Context Recall:    {data.get('avg_context_recall', 0):.2%}")
    print("=" * 70 + "\n")

    failure_buckets = {
        "ans_precision_drop": [], # Answer Precision < 0.95
        "ans_recall_drop": [],    # Answer Recall < 0.95
        "ctx_precision_drop": [], # Context Precision < 0.95
        "ctx_recall_drop": [],    # Context Recall < 0.95
        "perfect_scores": []      # All 4 >= 0.95
    }

    for q in questions:
        qid = q.get("id")
        ap = q.get("answer_precision", 0)
        ar = q.get("answer_recall", 0)
        cp = q.get("context_precision", 0)
        cr = q.get("context_recall", 0)

        if ap >= 0.95 and ar >= 0.95 and cp >= 0.95 and cr >= 0.95:
            failure_buckets["perfect_scores"].append(qid)
        else:
            if ap < 0.95:
                failure_buckets["ans_precision_drop"].append((qid, ap, q))
            if ar < 0.95:
                failure_buckets["ans_recall_drop"].append((qid, ar, q))
            if cp < 0.95:
                failure_buckets["ctx_precision_drop"].append((qid, cp, q))
            if cr < 0.95:
                failure_buckets["ctx_recall_drop"].append((qid, cr, q))

    print(f"Perfect Questions (>= 0.95 all metrics): {len(failure_buckets['perfect_scores'])} / {len(questions)}")
    print(f"Answer Precision Drops (< 0.95):          {len(failure_buckets['ans_precision_drop'])}")
    print(f"Answer Recall Drops (< 0.95):             {len(failure_buckets['ans_recall_drop'])}")
    print(f"Context Precision Drops (< 0.95):          {len(failure_buckets['ctx_precision_drop'])}")
    print(f"Context Recall Drops (< 0.95):             {len(failure_buckets['ctx_recall_drop'])}")
    print("\n" + "-" * 70)

    # Detailed triage for drops
    if failure_buckets["ans_precision_drop"]:
        print("\n--- Top Answer Precision Drops (Unsupported / Extra Claims) ---")
        for qid, score, q in failure_buckets["ans_precision_drop"][:5]:
            detail = q.get("answer_detail", {})
            extras = detail.get("extra_ids", [])
            print(f"Question {qid} (Score: {score:.2f}) -> {len(extras)} extra points: {extras[:3]}")

    if failure_buckets["ans_recall_drop"]:
        print("\n--- Top Answer Recall Drops (Missing Points) ---")
        for qid, score, q in failure_buckets["ans_recall_drop"][:5]:
            detail = q.get("answer_detail", {})
            misses = detail.get("missing_ids", [])
            print(f"Question {qid} (Score: {score:.2f}) -> {len(misses)} missing points: {misses[:3]}")

    if failure_buckets["ctx_precision_drop"]:
        print("\n--- Top Context Precision Drops (Noisy Retrieved Chunks) ---")
        for qid, score, q in failure_buckets["ctx_precision_drop"][:5]:
            print(f"Question {qid} (Score: {score:.2f}) -> Retrieved {q.get('num_retrieved_chunks')} chunks")

    if failure_buckets["ctx_recall_drop"]:
        print("\n--- Top Context Recall Drops (Insufficient Benchmark Chunks) ---")
        for qid, score, q in failure_buckets["ctx_recall_drop"][:5]:
            print(f"Question {qid} (Score: {score:.2f}) -> Retrieved {q.get('num_retrieved_chunks')} / Benchmark {q.get('num_benchmark_chunks')}")

if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "val"
    res_file = os.path.join(os.path.dirname(__file__), f"results_{split}.json")
    diagnose_evaluation_results(res_file)
