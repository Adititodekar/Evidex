import json

with open('eval/results_train.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print(f"ANSWER METRICS ANALYSIS (N={len(data['per_question'])})")
print("=" * 60)

for q in data['per_question']:
    qid = q.get('id')
    detail = q.get('answer_detail', {})
    ap_map = detail.get('agent_points', {})
    bp_map = detail.get('benchmark_points', {})
    matched = detail.get('matched_ids', [])
    extras = detail.get('extra_ids', [])
    misses = detail.get('missing_ids', [])
    
    agent_text = " ".join(ap_map.values())
    agent_words = len(agent_text.split())
    
    bp_text = " ".join(bp_map.values())
    bp_words = len(bp_text.split())
    
    print(f"[{qid}] Agent Points: {len(ap_map)} (~{agent_words} words) | Gold Points: {len(bp_map)} (~{bp_words} words)")
    print(f"      Ans Prec: {q.get('answer_precision',0):.2%} (Extras: {len(extras)}) | Ans Recall: {q.get('answer_recall',0):.2%} (Misses: {len(misses)}, Matched: {len(matched)})")
    print(f"      Context Prec: {q.get('context_precision',0):.2%} | Context Recall: {q.get('context_recall',0):.2%} | Ret Chunks: {q.get('num_retrieved_chunks')}")
