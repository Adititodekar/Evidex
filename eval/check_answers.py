import json

with open('eval/results_train.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Evaluated questions: {len(data['per_question'])}")
word_counts = []
for i, q in enumerate(data['per_question']):
    ans = q.get('ai_answer', '')
    wc = len(ans.split())
    word_counts.append(wc)
    print(f"Q {q.get('id', i+1)}: ai_words={wc}, ans_prec={q.get('answer_precision',0):.2f}, ans_rec={q.get('answer_recall',0):.2f}, ctx_prec={q.get('context_precision',0):.2f}, ctx_rec={q.get('context_recall',0):.2f}")

if word_counts:
    print(f"Average AI Answer Words: {sum(word_counts)/len(word_counts):.1f}")
