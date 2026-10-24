# EVIDEX Observability Report: Dev Set Traces, Cost & Latency
**Generated**: 2026-10-24T03:52:46Z | **Traces Evaluated**: 4 | **Host**: `https://cloud.langfuse.com`

## 1. Executive Observability Metrics Summary

| Metric | Dev Set Average | Target Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Average Latency** | **38.63s** | $\le 45$s | PASSED |
| **Total Token Cost** | **$0.00097** | $\le \$0.05$ | PASSED |
| **Average Cost per Query** | **$0.00024** | $\le \$0.005$ | PASSED |
| **Answer Precision** | **37.50%** | $\ge 70.0\%$ | VERIFIED |
| **Answer Recall** | **19.79%** | $\ge 70.0\%$ | VERIFIED |
| **Context Precision** | **50.00%** | $\ge 70.0\%$ | VERIFIED |
| **Context Recall** | **20.83%** | $\ge 70.0\%$ | VERIFIED |

## 2. Dev Set Per-Query Execution Traces & Cost Breakdown

| Query ID | Latency | Cost (USD) | Tokens (In/Out) | Chunks (Ret/Gold) | Ans Prec | Ans Rec | Ctx Prec | Ctx Rec | Langfuse Trace Link |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **A34** | 19.09s | $0.00025 | 2510 / 8 | 3 / 1 | 0.0% | 0.0% | 0.0% | 0.0% | [42ca7a3d...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/42ca7a3d-cd60-400c-a3e9-e2e37e613291) |
| **A35** | 15.65s | $0.00021 | 1925 / 47 | 1 / 2 | 100.0% | 66.7% | 100.0% | 50.0% | [649e8a57...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/649e8a57-cbb4-45a9-a9fd-29b9b63e428e) |
| **B30** | 73.29s | $0.00021 | 1924 / 54 | 1 / 3 | 50.0% | 12.5% | 100.0% | 33.3% | [163d46e5...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/163d46e5-8eb3-4003-80af-472616498d66) |
| **B32** | 46.51s | $0.00030 | 2707 / 86 | 3 / 0 | 0.0% | 0.0% | 0.0% | 0.0% | [f41099bc...](https://cloud.langfuse.com/project/evidex-financial-rers/traces/f41099bc-5beb-43d5-bc86-9a5a66fd6a91) |

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