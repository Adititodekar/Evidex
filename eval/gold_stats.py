"""
Inspect benchmark answer lengths across the 70 tune questions.
"""
import os
import json

bench_path = "Train/Benchmarks/benchmark_100.jsonl"
splits_path = "eval/splits.json"

with open(splits_path, "r", encoding="utf-8") as f:
    splits = json.load(f)

train_ids = set(splits.get("train_ids", []))

questions = []
with open(bench_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            item = json.loads(line)
            if item["id"] in train_ids:
                questions.append(item)

lengths_by_type = {"A": [], "B": [], "C": []}
overall_lengths = []

gold_chunks_by_type = {"A": [], "B": [], "C": []}
overall_gold_chunks = []

for q in questions:
    t = q["id"][0]
    ans = q.get("benchmark_answer", "")
    words = len(ans.split())
    lengths_by_type[t].append(words)
    overall_lengths.append(words)
    
    chunks = sum(len(c_list) for c_list in q.get("benchmark_chunks_w_metadata", {}).values())
    gold_chunks_by_type[t].append(chunks)
    overall_gold_chunks.append(chunks)

print("=" * 60)
print(f"BENCHMARK GOLD STATS (N={len(questions)})")
print("=" * 60)
for t in ["A", "B", "C"]:
    lens = lengths_by_type[t]
    chks = gold_chunks_by_type[t]
    print(f"Type {t}: Avg Gold Words = {sum(lens)/len(lens):.1f} (min={min(lens)}, max={max(lens)}) | Avg Gold Chunks = {sum(chks)/len(chks):.1f} (median={sorted(chks)[len(chks)//2]})")

print("-" * 60)
print(f"OVERALL: Avg Gold Words = {sum(overall_lengths)/len(overall_lengths):.1f} (min={min(overall_lengths)}, max={max(overall_lengths)}) | Avg Gold Chunks = {sum(overall_gold_chunks)/len(overall_gold_chunks):.1f} (median={sorted(overall_gold_chunks)[len(overall_gold_chunks)//2]})")
