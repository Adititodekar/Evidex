"""
Diagnose the 10 worst questions on the 70-question tune split.
Checks:
- Was the right document retrieved?
- Was the period/sibling correct?
- Were the relevant pages/sections missing?
"""
import os
import sys
import json
import logging
from typing import Dict, Any, List, Set, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from ingest.index_build import CollectionIndex, get_collection_dir
from retrieve.assemble import execute_retrieval_pipeline
from eval.proxy_metrics import normalize_doc_name

benchmark_path = settings.BENCHMARKS_PATH
splits_path = os.path.join(os.path.dirname(__file__), "splits.json")
with open(splits_path, "r", encoding="utf-8") as f:
    splits = json.load(f)

train_ids = set(splits.get("train_ids", []))

all_questions = {}
with open(benchmark_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            item = json.loads(line)
            if item["id"] in train_ids:
                all_questions[item["id"]] = item

col_idx = CollectionIndex("train")
col_dir = get_collection_dir("train")
siblings_path = os.path.join(col_dir, "siblings.json")
sibling_table = {}
if os.path.exists(siblings_path):
    with open(siblings_path, "r", encoding="utf-8") as f:
        sibling_table = json.load(f)

evaluated = []

for qid in splits.get("train_ids", []):
    q = all_questions[qid]
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

    retrieved_chunks, trace, _ = execute_retrieval_pipeline(query_text, col_idx, sibling_table)
    ret_docs = set(c.get("doc_id", c.get("document", "")) for c in retrieved_chunks)
    ret_pages = set((c.get("doc_id", c.get("document", "")), c.get("page", 0)) for c in retrieved_chunks)

    doc_rec = len(gold_docs & ret_docs) / len(gold_docs) if gold_docs else 1.0
    page_rec = len(gold_pages & ret_pages) / len(gold_pages) if gold_pages else 1.0
    page_prec = len(gold_pages & ret_pages) / len(ret_pages) if ret_pages else 0.0

    # Triage root cause
    if doc_rec == 0.0:
        cause = "WRONG_DOCUMENT: Surviving docs missed gold doc entirely"
    elif doc_rec < 1.0:
        cause = "PARTIAL_DOCUMENT: Multi-doc question missed one or more gold docs"
    elif page_rec < 0.10:
        cause = "MISSING_SECTIONS: Got right doc, but budget/router missed gold sections/pages"
    elif len(retrieved_chunks) < 35 and page_rec < 0.25:
        cause = "BUDGET_CAP: Budget capped retrieval far below gold chunk count"
    else:
        cause = "ROUTER_FILTER_MISS: Router scored wrong sections or verification filtered gold pages"

    evaluated.append({
        "id": qid,
        "type": qid[0],
        "query": query_text[:80] + "...",
        "gold_docs": list(gold_docs),
        "ret_docs": list(ret_docs),
        "doc_rec": doc_rec,
        "page_rec": page_rec,
        "page_prec": page_prec,
        "ret_chunks": len(retrieved_chunks),
        "gold_chunks": sum(len(cl) for cl in gold_meta.values()),
        "gold_pages_count": len(gold_pages),
        "cause": cause
    })

# Sort by page recall ascending
evaluated.sort(key=lambda x: (x["page_rec"], x["doc_rec"]))

print("\n" + "=" * 90)
print("10 WORST QUESTIONS DIAGNOSTIC TRIAGE (Tune Split)")
print("=" * 90)
for i, item in enumerate(evaluated[:10], 1):
    print(f"\n#{i:02d} [{item['id']}] (Type {item['type']}) Page Rec: {item['page_rec']:.1%} | Doc Rec: {item['doc_rec']:.1%} | Ret/Gold Chunks: {item['ret_chunks']}/{item['gold_chunks']}")
    print(f"    Query: {item['query']}")
    print(f"    Gold Docs: {item['gold_docs']}")
    print(f"    Ret Docs:  {item['ret_docs']}")
    print(f"    Primary Cause: {item['cause']}")

with open("eval/worst_10_diagnosis.json", "w", encoding="utf-8") as f:
    json.dump(evaluated[:10], f, indent=2)
