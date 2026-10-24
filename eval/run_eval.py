"""
Official Benchmark Evaluation Pipeline.
Runs EVIDEX RERS against the benchmark using the verbatim official evaluator (RAGMetricsEvaluator).
Evaluates Answer Precision, Answer Recall, Context Precision, and Context Recall.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from eval.official_eval import OpenCodeClient, RAGMetricsEvaluator
from ingest.index_build import CollectionIndex, get_collection_dir
from retrieve.assemble import execute_retrieval_pipeline
from answer.generate import generate_answer

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_runner")

def load_splits() -> Dict[str, List[str]]:
    splits_path = os.path.join(os.path.dirname(__file__), "splits.json")
    with open(splits_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_benchmark_questions() -> Dict[str, Dict[str, Any]]:
    bench_path = settings.BENCHMARKS_PATH
    questions = {}
    with open(bench_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                questions[item["id"]] = item
    return questions

def run_evaluation(
    split: str = "val",
    max_questions: int = None,
    collection_name: str = "train",
    output_file: str = None
) -> Dict[str, Any]:
    """
    Executes the official evaluation for a given split ('val', 'train', or 'all').
    """
    splits = load_splits()
    all_questions = load_benchmark_questions()

    if split == "val":
        target_ids = splits.get("val_ids", [])
    elif split == "train":
        target_ids = splits.get("train_ids", [])
    elif split == "all":
        target_ids = list(all_questions.keys())
    else:
        raise ValueError(f"Unknown split '{split}'. Must be 'val', 'train', or 'all'.")

    if max_questions:
        target_ids = target_ids[:max_questions]

    selected_questions = [all_questions[qid] for qid in target_ids if qid in all_questions]
    print(f"\n=======================================================")
    print(f"STARTING EVALUATION: Split='{split}' ({len(selected_questions)} questions)")
    print(f"Collection: '{collection_name}' | Model: '{settings.ANSWER_MODEL}'")
    print(f"=======================================================\n")

    # Initialize Evaluator with resilient adapter for JSON array outputs
    class RobustJudgeClient(OpenCodeClient):
        def call_structured(self, system_prompt: str, user_prompt: str, max_tokens: int = 10000,
                             temperature: float = 0, max_retries: int = 3) -> dict:
            data = super().call_structured(system_prompt, user_prompt, max_tokens, temperature, max_retries)
            if isinstance(data, list):
                if "points" in user_prompt:
                    return {"points": data}
                elif "verdicts" in user_prompt:
                    return {"verdicts": data}
                return {"items": data}
            return data

    api_key = settings.GEMINI_API_KEY or settings.OPENCODE_API_KEY
    judge_client = RobustJudgeClient(
        api_key=api_key,
        model=settings.GEMINI_MODEL,
        base_url=settings.GEMINI_BASE_URL
    )
    evaluator = RAGMetricsEvaluator(judge_client)

    # Initialize Ingestion / Index
    col_idx = CollectionIndex(collection_name)
    col_dir = get_collection_dir(collection_name)
    siblings_path = os.path.join(col_dir, "siblings.json")
    sibling_table = {}
    if os.path.exists(siblings_path):
        with open(siblings_path, "r", encoding="utf-8") as f:
            sibling_table = json.load(f)

    results = []
    t_start = time.time()

    for idx, q_item in enumerate(selected_questions, 1):
        qid = q_item["id"]
        query = q_item["question"]
        gold_answer = q_item["benchmark_answer"]
        gold_meta = q_item.get("benchmark_chunks_w_metadata", {})

        # Extract gold chunk texts
        gold_chunks = []
        for doc_name, chunks in gold_meta.items():
            for c in chunks:
                gold_chunks.append(c.get("content", ""))

        t0 = time.time()
        print(f"[{idx}/{len(selected_questions)}] Querying and evaluating {qid}...", end=" ", flush=True)

        # 1. RERS Retrieval
        verified_chunks, trace, context_str = execute_retrieval_pipeline(query, col_idx, sibling_table)

        # 2. Answer Generation
        ai_answer, usage = generate_answer(query, context_str)

        # 3. Official Metric Evaluation
        retrieved_chunk_texts = [c["text"] for c in verified_chunks]
        metrics = evaluator.evaluate_single(
            query=query,
            ai_answer=ai_answer,
            benchmark_answer=gold_answer,
            retrieved_chunks=retrieved_chunk_texts,
            benchmark_chunks=gold_chunks
        )

        lat = time.time() - t0
        metrics["id"] = qid
        metrics["query"] = query
        metrics["latency_s"] = round(lat, 2)
        metrics["num_retrieved_chunks"] = len(verified_chunks)
        metrics["num_benchmark_chunks"] = len(gold_chunks)
        results.append(metrics)

        print(
            f"Done! -> AnsP={metrics['answer_precision']:.2f} AnsR={metrics['answer_recall']:.2f} | "
            f"CtxP={metrics['context_precision']:.2f} CtxR={metrics['context_recall']:.2f} | "
            f"Chunks={len(verified_chunks)} ({lat:.1f}s)",
            flush=True
        )

    # Compute summary
    def avg(key):
        return sum(r[key] for r in results) / len(results) if results else 0.0

    summary = {
        "split": split,
        "num_questions": len(results),
        "avg_answer_precision": round(avg("answer_precision"), 4),
        "avg_answer_recall": round(avg("answer_recall"), 4),
        "avg_context_precision": round(avg("context_precision"), 4),
        "avg_context_recall": round(avg("context_recall"), 4),
        "avg_latency_s": round(avg("latency_s"), 2),
        "total_elapsed_s": round(time.time() - t_start, 2),
        "per_question": results
    }

    print("\n" + "=" * 60)
    print(f"EVALUATION SUMMARY ({split.upper()} SET - {len(results)} QUESTIONS)")
    print(f"Answer Precision:    {summary['avg_answer_precision']:.2%}")
    print(f"Answer Recall:       {summary['avg_answer_recall']:.2%}")
    print(f"Context Precision:   {summary['avg_context_precision']:.2%}")
    print(f"Context Recall:      {summary['avg_context_recall']:.2%}")
    print(f"Average Latency:     {summary['avg_latency_s']}s")
    print(f"Total Time:          {summary['total_elapsed_s']}s")
    print("=" * 60 + "\n")

    out_path = output_file or os.path.join(os.path.dirname(__file__), f"results_{split}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Full results saved to {out_path}")

    return summary

if __name__ == "__main__":
    split_arg = sys.argv[1] if len(sys.argv) > 1 else "val"
    limit_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_evaluation(split=split_arg, max_questions=limit_arg)
