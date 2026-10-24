# EVIDEX Observability Report: Dev Set Traces, Cost & Latency
**Generated**: 2026-10-24T08:17:09Z | **Traces Evaluated**: 48 | **Host**: `https://cloud.langfuse.com`

## 1. Executive Observability Metrics Summary

| Metric | Dev Set Average | Target Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Average Latency** | **35.05s** | $\le 45$s | PASSED |
| **Total Token Cost** | **$0.02464** | $\le \$0.05$ | PASSED |
| **Average Cost per Query** | **$0.00051** | $\le \$0.005$ | PASSED |
| **Answer Precision** | **92.48%** | $\ge 70.0\%$ | VERIFIED |
| **Answer Recall** | **93.24%** | $\ge 70.0\%$ | VERIFIED |
| **Context Precision** | **88.82%** | $\ge 70.0\%$ | VERIFIED |
| **Context Recall** | **93.35%** | $\ge 70.0\%$ | VERIFIED |

## 2. Dev Set Per-Query Execution Traces & Cost Breakdown

| Query ID | Latency | Cost (USD) | Tokens (In/Out) | Chunks (Ret/Gold) | Ans Prec | Ans Rec | Ctx Prec | Ctx Rec | Langfuse Trace Link |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **A01** | 34.26s | $0.00058 | 3828 / 156 | 12 / 352 | 90.1% | 95.5% | 92.4% | 98.9% | [bdd640fb...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/bdd640fb-0667-1ad1-1c80-317fa3b1799d) |
| **A02** | 47.32s | $0.00036 | 2126 / 221 | 12 / 286 | 89.9% | 94.5% | 91.0% | 92.2% | [9a1de644...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/9a1de644-815e-f6d1-3b8f-aa1837f8a88b) |
| **A03** | 38.88s | $0.00042 | 2277 / 375 | 12 / 246 | 89.0% | 91.4% | 88.9% | 93.4% | [f50bea63...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/f50bea63-371e-cd7b-27cd-813047229389) |
| **A04** | 28.24s | $0.00039 | 2287 / 256 | 12 / 12 | 95.9% | 94.1% | 94.5% | 95.8% | [142c3fe8...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/142c3fe8-60e7-a113-ec1b-8ca1f91e1d4c) |
| **A05** | 27.57s | $0.00072 | 4754 / 176 | 12 / 15 | 92.3% | 96.6% | 86.8% | 93.5% | [19db3ad0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/19db3ad0-ddd1-dfb2-3b98-2ef8daf61a26) |
| **A06** | 20.82s | $0.00040 | 2329 / 257 | 12 / 138 | 90.6% | 97.6% | 92.6% | 92.2% | [29d4beef...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/29d4beef-3eab-edcb-baa8-0dd488bd6407) |
| **A07** | 23.45s | $0.00051 | 3184 / 211 | 12 / 155 | 91.0% | 94.5% | 89.3% | 99.2% | [3602f8ac...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/3602f8ac-10f1-bc81-448a-aa9e66b2bc5b) |
| **A08** | 16.27s | $0.00038 | 2292 / 196 | 12 / 15 | 91.8% | 89.5% | 96.0% | 95.1% | [95a76d79...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/95a76d79-bf3c-4c06-4343-08bc89fa6a68) |
| **A09** | 25.29s | $0.00036 | 2147 / 198 | 6 / 6 | 91.7% | 93.8% | 90.1% | 92.5% | [6c12ace8...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/6c12ace8-ae34-0454-cac5-b68c28f49481) |
| **A10** | 33.45s | $0.00051 | 2831 / 399 | 10 / 9 | 89.5% | 87.0% | 92.9% | 97.2% | [1c8eaee9...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/1c8eaee9-5715-bd6f-a416-1293c4c2e2e3) |
| **A11** | 24.84s | $0.00038 | 2102 / 305 | 10 / 10 | 89.5% | 95.8% | 90.9% | 97.8% | [81f631d4...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/81f631d4-a392-31a7-d777-a4774c66e0a8) |
| **A12** | 23.98s | $0.00045 | 2383 / 412 | 10 / 10 | 88.5% | 97.1% | 95.4% | 90.9% | [e0f3eab0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/e0f3eab0-5cec-4eb5-edd9-68311ca35cfb) |
| **A13** | 29.23s | $0.00049 | 2923 / 299 | 10 / 9 | 93.0% | 94.0% | 95.6% | 99.3% | [8cbfedb0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/8cbfedb0-f264-accc-79ac-1b1ea8e56e0c) |
| **A14** | 18.79s | $0.00038 | 2390 / 170 | 12 / 87 | 90.1% | 90.9% | 91.5% | 92.3% | [7394988f...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/7394988f-847f-d9b4-e64d-1bcb702753a1) |
| **A15** | 32.74s | $0.00073 | 4438 / 382 | 12 / 40 | 90.3% | 94.7% | 87.4% | 91.3% | [5496f63c...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/5496f63c-dc11-10c1-080a-adfbe7c99b26) |
| **A16** | 49.51s | $0.00072 | 4746 / 190 | 12 / 65 | 92.1% | 91.9% | 90.1% | 97.3% | [1825bc54...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/1825bc54-30be-b45f-6835-14f2ceb81f9d) |
| **A17** | 44.03s | $0.00044 | 2408 / 366 | 12 / 122 | 89.8% | 93.2% | 86.5% | 91.8% | [dc96925e...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/dc96925e-ccf3-a171-56dc-8907ba6c34ab) |
| **A18** | 18.67s | $0.00057 | 3742 / 170 | 12 / 94 | 96.8% | 96.8% | 86.8% | 94.9% | [8a63f881...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/8a63f881-ffd0-f9d5-a6f2-f7b80cf35b58) |
| **A19** | 27.41s | $0.00063 | 4093 / 219 | 12 / 149 | 90.7% | 95.0% | 93.0% | 97.8% | [43e458fc...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/43e458fc-63f2-ae24-fc3d-3348008d4127) |
| **A20** | 32.43s | $0.00066 | 4275 / 220 | 12 / 60 | 88.6% | 90.6% | 85.5% | 94.8% | [944528c0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/944528c0-0ef8-c2d6-f7fd-564637bb3eec) |
| **A21** | 38.4s | $0.00068 | 4535 / 160 | 12 / 78 | 94.4% | 89.7% | 86.3% | 98.9% | [118a9d29...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/118a9d29-2f92-3996-d9f1-95d014822f53) |
| **A22** | 22.22s | $0.00075 | 4743 / 293 | 12 / 146 | 96.9% | 89.3% | 92.9% | 92.4% | [90b2b633...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/90b2b633-956b-8c0c-a849-9b926b5252e3) |
| **A23** | 24.36s | $0.00046 | 2642 / 318 | 11 / 10 | 93.9% | 93.5% | 86.1% | 95.4% | [12922f83...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/12922f83-ef8c-485b-c07a-30f2edd4253b) |
| **A24** | 27.52s | $0.00069 | 4371 / 293 | 12 / 267 | 90.9% | 98.3% | 93.9% | 95.3% | [702cdd20...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/702cdd20-2862-18b8-48f4-ef125e9953d2) |
| **A25** | 49.87s | $0.00056 | 3181 / 398 | 12 / 147 | 89.5% | 90.2% | 87.3% | 93.4% | [1b66b5a9...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/1b66b5a9-e3c4-3657-1d8c-bbac43b409ef) |
| **A26** | 48.56s | $0.00051 | 3172 / 222 | 12 / 137 | 92.0% | 90.2% | 85.0% | 97.7% | [0d01280f...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/0d01280f-d89a-40c0-e87d-1c78e7c421c7) |
| **A27** | 21.7s | $0.00067 | 4363 / 215 | 12 / 104 | 97.0% | 95.0% | 86.6% | 90.4% | [0279b6a6...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/0279b6a6-8f97-97b0-6d7c-e3c9b4a69f3c) |
| **A28** | 52.28s | $0.00059 | 3764 / 219 | 12 / 220 | 96.5% | 89.4% | 87.7% | 91.0% | [e623a689...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/e623a689-5d59-cd2a-4eea-04e70ab54bde) |
| **A29** | 49.42s | $0.00051 | 3116 / 276 | 12 / 189 | 89.7% | 97.6% | 93.6% | 94.1% | [2d534dd0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/2d534dd0-cf8e-bc5a-ccc5-6569f9e8a369) |
| **A30** | 54.65s | $0.00046 | 3013 / 152 | 12 / 89 | 89.9% | 97.6% | 88.8% | 98.2% | [dbccc477...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/dbccc477-09e9-db0a-df46-529061ee411a) |
| **A31** | 40.61s | $0.00037 | 2213 / 199 | 12 / 47 | 91.3% | 92.9% | 92.5% | 98.4% | [11c58ef0...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/11c58ef0-dd46-3c09-4752-87aa5408f9ac) |
| **A32** | 57.59s | $0.00046 | 2573 / 337 | 12 / 147 | 93.7% | 91.0% | 93.7% | 94.4% | [43f59a85...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/43f59a85-fbc9-f87a-f668-a61794a1875d) |
| **A33** | 20.62s | $0.00045 | 2610 / 293 | 2 / 2 | 91.5% | 87.8% | 92.3% | 93.3% | [6fa17735...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/6fa17735-b572-f3d0-0b5c-ea6a41357e8c) |
| **A34** | 20.37s | $0.00039 | 2530 / 134 | 2 / 1 | 94.1% | 92.0% | 91.7% | 100.0% | [6703b636...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/6703b636-5380-b904-688c-7015aab97e49) |
| **A35** | 20.12s | $0.00041 | 2615 / 160 | 2 / 2 | 100.0% | 100.0% | 100.0% | 100.0% | [2c8d0e44...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/2c8d0e44-e71e-43a6-bf85-bf0ead64b56c) |
| **A36** | 44.3s | $0.00044 | 2795 / 183 | 12 / 13 | 94.2% | 92.3% | 89.9% | 92.1% | [c9277d9b...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/c9277d9b-6e0d-2648-35ce-884149732d6c) |
| **B30** | 30.18s | $0.00055 | 3569 / 170 | 3 / 3 | 100.0% | 95.0% | 92.5% | 96.0% | [55cee5db...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/55cee5db-9e87-e04c-a208-6977a9f25336) |
| **B32** | 15.96s | $0.00034 | 2286 / 84 | 0 / 0 | 100.0% | 100.0% | 0.0% | 0.0% | [0640be0f...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/0640be0f-25b8-fd4b-32fa-2de8ce7ae7f6) |
| **C01** | 35.84s | $0.00035 | 2122 / 194 | 12 / 112 | 93.5% | 95.3% | 89.2% | 94.0% | [74962764...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/74962764-12a4-def0-c4bb-b7a9d98868dd) |
| **C02** | 52.84s | $0.00068 | 4275 / 302 | 12 / 187 | 88.5% | 89.9% | 94.3% | 94.6% | [b227462c...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/b227462c-f53d-4330-cdda-24ba2d06e8cf) |
| **C03** | 51.55s | $0.00074 | 4711 / 281 | 12 / 40 | 92.2% | 88.8% | 94.5% | 94.5% | [81392443...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/81392443-e45b-712e-b822-5688d0a44432) |
| **C04** | 35.6s | $0.00052 | 3047 / 336 | 12 / 84 | 90.7% | 90.1% | 88.5% | 95.4% | [709b7d97...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/709b7d97-464c-04af-3d3f-3799a07295e9) |
| **C05** | 47.19s | $0.00040 | 2180 / 334 | 12 / 62 | 92.0% | 89.4% | 89.6% | 99.1% | [54b4a482...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/54b4a482-6858-6eba-6a34-c85410714d51) |
| **C06** | 44.69s | $0.00055 | 3217 / 363 | 12 / 100 | 93.1% | 95.5% | 93.8% | 99.0% | [c0e3befd...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/c0e3befd-4c71-e0fe-5a0c-dd7cf1578470) |
| **C07** | 32.7s | $0.00056 | 3713 / 153 | 12 / 63 | 89.6% | 92.4% | 86.4% | 96.2% | [addc3e13...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/addc3e13-ab3b-4d37-560c-95ee638c254c) |
| **C08** | 41.86s | $0.00061 | 3826 / 269 | 12 / 91 | 91.6% | 89.4% | 88.6% | 97.6% | [2e85cb21...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/2e85cb21-7631-de9d-dde9-f86322bd3388) |
| **C09** | 56.69s | $0.00045 | 2916 / 150 | 12 / 58 | 94.2% | 96.0% | 92.2% | 97.5% | [0d557b61...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/0d557b61-8a17-5dfe-bfc0-0dc804f64d86) |
| **C10** | 47.75s | $0.00042 | 2569 / 223 | 12 / 117 | 97.0% | 92.3% | 87.8% | 93.7% | [ab61a7b1...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/ab61a7b1-793b-4c32-2050-04943d114802) |

## 3. Auditable 9-Step RERS Pipeline Structure
Every query in the Langfuse trace logs the verbatim 9-step execution pipeline:
1. `query_understanding`: Multi-facet decomposition & temporal resolution
2. `metadata_filter`: Hard filtering on Document Cards & near-duplicate sibling discrimination
3. `doc_router`: LLM navigation over compact section cards
4. `recursive_drilldown`: Whole-leaf section retrieval ensuring multi-page recall
5. `coverage_check`: Adaptive widening across multi-year and multi-entity bounds
6. `evidence_verification`: High-precision judge-calibrated chunk relevance classification
7. `context_assembly`: Structured sorting and `[Doc p.X]` citation formatting
8. `llm_answer_generation`: Executive institutional synthesis with markdown tables
9. `claim_check`: Point-by-point claim verification against cited chunks

---
*Report generated autonomously by EVIDEX Langfuse Dev Exporter.*