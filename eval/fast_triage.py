"""
Fast deterministic triage of the 70 tune benchmark questions.
Compares query entities, periods, and gold documents to isolate failure classes.
"""
import os
import re
import json

bench_path = "Train/Benchmarks/benchmark_100.jsonl"
splits_path = "eval/splits.json"
cards_dir = "data/train/cards"
siblings_path = "data/train/siblings.json"

with open(splits_path, "r", encoding="utf-8") as f:
    splits = json.load(f)
train_ids = set(splits.get("train_ids", []))

questions = {}
with open(bench_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            item = json.loads(line)
            if item["id"] in train_ids:
                questions[item["id"]] = item

doc_cards = {}
for fname in os.listdir(cards_dir):
    if fname.endswith(".card.json"):
        with open(os.path.join(cards_dir, fname), "r", encoding="utf-8") as f:
            c = json.load(f)
            doc_cards[c["doc_id"]] = c

with open(siblings_path, "r", encoding="utf-8") as f:
    sibling_table = json.load(f)

DOC_EQUIV = {
    "Guidelines on Management of Problem Loans.pdf": "SAMA_EN_3575_VER1.pdf",
    "2026-05960.pdf": "91fr14908.pdf",
    "fact-sheet-20260319.pdf": "fact-sheet-SUMMARY.pdf",
}

def norm_doc(d):
    return DOC_EQUIV.get(d, d)

triage_results = []

for qid in splits.get("train_ids", []):
    q = questions[qid]
    qtext = q.get("question", "")
    gold_docs = [norm_doc(d) for d in q.get("benchmark_chunks_w_metadata", {}).keys()]
    gold_chunks = sum(len(cl) for cl in q.get("benchmark_chunks_w_metadata", {}).values())
    
    # 1. Check entity mentions
    detected_entities = []
    for d, card in doc_cards.items():
        ent = card.get("entity", "").lower()
        if ent and len(ent) > 3 and ent in qtext.lower():
            detected_entities.append(d)

    # 2. Check period mentions
    detected_periods = re.findall(r'\b(20\d{2})\b', qtext)

    # 3. Check sibling status
    is_sibling_doc = any(d in sibling_table for d in gold_docs)

    triage_results.append({
        "id": qid,
        "type": qid[0],
        "query": qtext[:75] + "...",
        "gold_docs": gold_docs,
        "gold_chunks": gold_chunks,
        "detected_entities": detected_entities,
        "detected_periods": detected_periods,
        "has_siblings": is_sibling_doc
    })

print("=" * 70)
print("TRIAGE SUMMARY ACROSS 70 QUESTIONS")
print("=" * 70)
multi_doc_q = [r for r in triage_results if len(r["gold_docs"]) > 1]
print(f"Multi-document Questions: {len(multi_doc_q)} / 70")
print(f"Questions targeting sibling documents: {sum(1 for r in triage_results if r['has_siblings'])} / 70")
print(f"Type C Questions without entity match: {sum(1 for r in triage_results if r['type'] == 'C' and not r['detected_entities'])} / 23")

print("\n--- SAMPLE TOUGH QUESTIONS ---")
for r in [r for r in triage_results if r['type'] == 'C'][:4] + [r for r in triage_results if len(r['gold_docs']) > 1][:3] + [r for r in triage_results if r['has_siblings']][:3]:
    print(f"[{r['id']}] (Type {r['type']}) Gold: {r['gold_docs']} (Gold chunks: {r['gold_chunks']})")
    print(f"     Query: {r['query']}")
