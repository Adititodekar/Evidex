# PLAN: Routed Evidence-Set Retrieval (RERS)
## 12-Hour Hackathon: Smart Knowledge Base for Agents

---

### 1. Executive Summary & Problem Framing

Modern RAG pipelines rely on shallow, vector-similarity top-$k$ retrieval that tops out around a ~0.6 precision and recall ceiling in production financial environments. Two core structural failure modes account for this breakdown:
1. **Failure Mode 1: Near-Duplicate / Highly Similar Documents**: Financial filings across successive fiscal years (e.g. FY2025 vs. FY2026), policy proposals vs. final rules, or staff memos vs. fact s
heets share nearly identical vocabulary and topical embeddings. Top-$k$ similarity fails to discriminate based on temporal scope, jurisdiction, or legal standing.
2. **Failure Mode 2: The Chunk-Size Dilemma**: Complex analyst queries require synthesizing wide evidence sets (frequently 30–80 pages). Increasing $k$ introduces substantial noise and token cost without ensuring comprehensive coverage of relevant sections.

The required evaluation threshold is **$\ge 0.95$ across all four metrics**:
- **Answer Precision**: (Points in AI response verified correct against benchmark) / (Total points in AI response)
- **Answer Recall**: (Points in AI response verified correct against benchmark) / (Total points in benchmark)
- **Context Precision**: (Retrieved chunks judged genuinely relevant) / (Total retrieved chunks)
- **Context Recall**: (Retrieved chunks judged genuinely relevant) / (Total benchmark chunks)

Our solution implements **Routed Evidence-Set Retrieval (RERS)**: a deterministic and hierarchical architecture that decouples corpus understanding (ingestion-time metadata and structured section trees) from query-time recursive navigation and strict LLM verification.

---

### 2. System Architecture: Routed Evidence-Set Retrieval (RERS)

```
[Ingestion: POST /index]
PDF -> Page Extraction (PyMuPDF + OCR fallback) 
    -> Structure Tree (TOC / Headings / Outlines)
    -> Exact-Page Paragraph Chunks (60-250 words, 1-based page)
    -> Dynamic Metadata Layer:
         * Document Cards (entity, type, period, status, scope, discriminating features)
         * Sibling Detection & Discrimination Table (near-duplicate clusters)
         * Section Cards (summaries, entities, page ranges)
    -> Local Multi-Vector Index (BGE-small + BM25) for candidate generation
    -> Storage: data/<collection_name>/ (SQLite metadata + FAISS/npy)

[Inference: POST /query]
Query 
  -> Step 1: query_understanding (facet decomposition, entities, resolved temporal scope, breadth)
  -> Step 2: metadata_filter (hard filter on Doc Cards + Sibling Discrimination)
  -> Step 3: doc_router (LLM navigates compact section cards per facet)
  -> Step 4: recursive_drilldown (leaf-section take-all guarantees complete multi-page recall)
  -> Step 5: coverage_check (deterministic facet evidence guard + widening)
  -> Step 6: evidence_verification (cheap batch classification on relevance, cap <= 150)
  -> Step 7: context_assembly (ordered by doc/page, facet grouping, [Doc p.X] tags)
  -> Step 8: llm_answer_generation (bottom-line, structured sections, comparison tables, exact citations)
  -> Step 9: claim_check (sentence-level fact verification against cited chunks)
  -> Output Response Contract (answer, chunks, step trace, usage) + Langfuse observability
```

---

### 3. Implementation Milestones & Acceptance Criteria

| Milestone | Scope & Deliverables | Acceptance Test |
| :--- | :--- | :--- |
| **M1: Ingestion & Extraction** | `ingest/pdf_extract.py`, `ingest/ocr.py`, `ingest/structure.py`, `ingest/chunker.py`. Exact 1-based page numbering, table markdown extraction, RapidOCR fallback for scanned PDFs (`SAMA_EN_3575_VER1.pdf`). | `tests/test_page_alignment.py`: $\ge 95\%$ text match on 200 sampled gold chunks from `benchmark_100.jsonl`. Scanned SAMA PDF yields non-empty text. |
| **M2: Metadata & Sibling Cards** | `ingest/cards.py`, `ingest/siblings.py`. Automatic LLM generation of Document Cards and Section Cards; sibling clustering to capture temporal and regulatory discriminators. | Spot check: 36/36 doc cards generated; Metal Coatings FY25 and FY26 identified as siblings with `period` discriminator. |
| **M3: Multi-Vector & BM25 Indexing** | `ingest/index_build.py`. BGE-small / e5-small local embedding + rank_bm25; multi-vector per chunk (text, summary, questions); named collection isolation under `data/<collection_name>/`. | Multi-collection isolation test: creating collection B does not mutate or overwrite collection A. |
| **M4: Query Decomposition & Navigation** | `retrieve/understand.py`, `retrieve/meta_filter.py`, `retrieve/router.py`, `retrieve/drilldown.py`, `retrieve/coverage.py`, `retrieve/verify.py`. Facet decomposition, card routing, whole-section retrieval, LLM verification. | Proxy evaluation on Train split: Document recall $\ge 0.98$, high page recall beating TF-IDF baseline (0.39). |
| **M5: Grounded Answer Generation** | `answer/generate.py`, `answer/claim_check.py`. Structured prompt matching gold benchmark style (Bottom line, headed sections, tables, `[Doc p.X]` citations, abstention on unanswerable questions like B32). | 5 end-to-end question tests with complete citations, valid step trace, and verified zero hallucinated claims. |
| **M6: API Server & Langfuse Tracing** | `app/api.py`, `app/llm.py`, `app/schemas.py`. Endpoints `POST /index` and `POST /query`; exact trace schema; Langfuse integration logging per-query cost and latency. | `tests/test_api_contract.py` passes; Langfuse exports valid spans and generation costs. |
| **M7: Evaluation & Improvement Loop** | `eval/official_eval.py` (verbatim from `Evaluation.ipynb`), `eval/run_eval.py`, `eval/proxy_metrics.py`, `eval/diagnose.py`, `eval/splits.json` (70/30 train/val). | Full evaluation run on validation set; iteration logged in `RUN_LOG.md` tracking all 4 metrics. |
| **M8: Deployment & Technical Writeup** | Server setup / Dockerfile, curl smoke scripts, calibrated ingestion time, `docs/WRITEUP.md` (2-3 pages PDF export). | Verified reachable API on server; comprehensive writeup summarizing architecture, trade-offs, and metrics. |

---

### 4. Integrity & Anti-Overfitting Safeguards

1. **Unmodified Official Evaluator**: `eval/official_eval.py` is copied verbatim from `Train/Evaluation/Evaluation.ipynb`. A dedicated test (`tests/test_eval_untouched.py`) hashes the classes and functions against the notebook to guarantee zero modifications.
2. **Strictly Corpus-Agnostic**: Zero hardcoding of document names, company names, years, or folder hierarchies. Metadata extraction operates purely on raw document contents. Relative temporal expressions ("latest report", "current proposal") resolve dynamically against extracted card periods.
3. **Handling Missing Documents & Distractors**:
   - 3 documents cited in gold benchmarks are missing from `Train/Documents` (`2026-05960.pdf`, `fact-sheet-20260319.pdf`, `Guidelines on Management of Problem Loans.pdf`).
   - 4 documents present are un-cited distractors.
   - Evaluation reports metrics across all questions as well as questions with all source documents present.
4. **Explicit Abstention Mechanism**: When information is absent from the corpus (e.g. Question B32), the system explicitly returns "not found in the provided documents" rather than generating speculative claims.

---

### 5. Risk Management & Mitigations

- **LLM Rate Limits & Latency**: OpenCode API calls will be executed with an asynchronous semaphore (limit 10-16), automatic exponential backoff on HTTP 429, and compact prompt structures (summaries rather than raw pages).
- **Ingestion Time Budget**: Page card summaries are constructed lazily or cached by content hash; document cards and section cards are batched.
- **Judge Token Limits**: Retrieved chunk sets are capped at $\le 150$ verified chunks to prevent token truncation during the official context evaluation step.
