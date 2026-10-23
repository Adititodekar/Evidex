# EVIDEX: Routed Evidence-Set Retrieval (RERS)
### High-Precision Knowledge Base Engine for Financial Research AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

---

## 1. Overview & Problem Statement

Standard retrieval systems (dense similarity search, hybrid RAG, reranking, HyDE, CRAG) plateau around a ~0.6 precision and recall ceiling in high-stakes financial domains. In financial research, a single hallucinated or misattributed fact can cause millions in losses.

Two core structural failure modes account for this ceiling:
1. **Near-Duplicate / Highly Similar Documents**: Financial filings across reporting years (e.g., Metal Coatings FY2025 vs FY2026), policy proposals vs. final rules, and staff memos share topical embeddings. Unfiltered similarity search cannot reliably discriminate based on temporal period, legal status, or scope.
2. **The Chunk-Size Dilemma**: Queries requiring multi-page synthesis (frequently 30–80 pages) fail when retrieving a fixed top-$k$ (e.g. top-20). Increasing $k$ inflates token costs and introduces irrelevant distractors without guaranteeing complete coverage.

**Target Evaluation Bar**: Answer Precision $\ge 0.95$, Answer Recall $\ge 0.95$, Context Precision $\ge 0.95$, Context Recall $\ge 0.95$.

---

## 2. Architecture: Routed Evidence-Set Retrieval (RERS)

EVIDEX replaces shallow top-$k$ similarity with a structured, hierarchical evidence-routing pipeline:

```
[ Ingestion: POST /index ]
PDF Documents (Zip)
   ├── Page-Aligned Text Extraction (1-based PDF index)
   ├── Table Detection -> Clean Structured Markdown
   ├── Scanned Page Fallback (RapidOCR / ONNX)
   ├── Section Tree Construction (TOC Bookmarks + Heading Detection)
   ├── Paragraph-Aware Exact-Page Chunking (60–250 words)
   ├── Dynamic Metadata Layer (Doc Cards, Sibling Clusters, Section Cards)
   └── Multi-Vector & BM25 Local Indexing (data/<collection_name>/)

[ Inference: POST /query ]
User Query
   ├── Step 1: query_understanding (Facet decomposition, temporal resolution, breadth budget)
   ├── Step 2: metadata_filter (Hard filter on Doc Cards + Sibling Discrimination)
   ├── Step 3: doc_router (LLM navigates compact section summaries per facet)
   ├── Step 4: recursive_drilldown (Leaf-section whole selection guarantees complete recall)
   ├── Step 5: coverage_check (Deterministic evidence bounds & adaptive widening)
   ├── Step 6: evidence_verification (Strict relevance classification, budget-capped)
   ├── Step 7: context_assembly (Ordered by Doc/Page, [Doc p.X] tags)
   ├── Step 8: llm_answer_generation (Bottom-line, structured sections, comparison tables)
   └── Step 9: claim_check (Sentence-level fact verification against cited chunks)
```

---

## 3. Repository Structure

```
├── .gitignore               # Strict exclusion of API keys, large binary PDFs, runtime cache
├── PLAN.md                  # Comprehensive architectural blueprint and milestones
├── RUN_LOG.md               # Empirical iteration and milestone test log
├── README.md                # System documentation
├── app/                     # FastAPI server and schemas
│   ├── api.py               # POST /index and POST /query endpoints
│   ├── config.py            # Environment configuration
│   ├── llm.py               # OpenCode client, cost tracking, Langfuse instrumentation
│   └── schemas.py           # Pydantic request/response models & trace schema
├── ingest/                  # Corpus extraction and ingestion pipeline
│   ├── pdf_extract.py       # Page extraction with 1-based indexing & table markdown
│   ├── ocr.py               # RapidOCR fallback for scanned PDFs
│   ├── structure.py         # Section hierarchy tree builder
│   ├── chunker.py           # Paragraph-aware chunker (strictly page-bounded)
│   ├── cards.py             # Document and section card generation
│   ├── siblings.py          # Near-duplicate clustering and discriminating fields
│   └── index_build.py       # Multi-vector and BM25 index constructor
├── retrieve/                # Query-time evidence routing pipeline
│   ├── understand.py        # Query facet decomposition & entity extraction
│   ├── meta_filter.py       # Metadata filtering & sibling discrimination
│   ├── router.py            # LLM section-card navigation
│   ├── drilldown.py         # Recursive leaf-section whole extraction
│   ├── coverage.py          # Deterministic facet coverage guard
│   ├── verify.py            # Evidence relevance classification
│   └── assemble.py          # Context assembly & citation grouping
├── answer/                  # Answer generation and verification
│   ├── generate.py          # Grounded synthesis in benchmark style
│   └── claim_check.py       # Point-by-point claim verification
├── eval/                    # Evaluation harness
│   ├── official_eval.py     # Verbatim official evaluator from Evaluation.ipynb
│   ├── run_eval.py          # Full dev evaluation runner
│   ├── proxy_metrics.py     # Cheap proxy metrics (doc/page recall, precision)
│   └── diagnose.py          # Diagnostic triage for failure modes
└── tests/                   # Verification and integrity unit tests
    ├── test_eval_untouched.py   # Cryptographic SHA-256 test of evaluation function
    └── test_page_alignment.py   # Page alignment test (100% on offset-0 compliant chunks)
```

---

## 4. API Specification

### `POST /index`
- **Input**: Multipart `file` (Zip archive of documents), form parameter `collection_name`.
- **Behavior**: Unzips securely, indexes pages, builds structure trees, extracts metadata cards, and stores data under isolated `data/<collection_name>/`.
- **Response**:
```json
{
  "status": "success",
  "collection_name": "train",
  "documents": 35,
  "pages": 6970,
  "chunks": 24500,
  "ocr_pages": 92,
  "seconds": 184.2
}
```

### `POST /query`
- **Input**: JSON `{"collection_name": "train", "query": "..."}`
- **Response Contract**:
```json
{
  "answer": "...",
  "chunks": [
    {
      "text": "...",
      "document": "BCBS-MarketRisk.pdf",
      "page": 12,
      "section": "3.1 Minimum Capital Requirements",
      "score": 0.98,
      "facet": "Market risk capital rules"
    }
  ],
  "trace": [
    {
      "step_name": "query_understanding",
      "description": "Decomposed query into 3 facets and resolved temporal period to FY2026",
      "input": {"query": "..."},
      "output": {"facets": ["..."], "entities": ["..."]}
    }
  ],
  "usage": {
    "input_tokens": 4200,
    "output_tokens": 850,
    "cost_usd": 0.0028,
    "latency_s": 8.42
  }
}
```

---

## 5. Verification & Testing

Run all unit tests:
```bash
python tests/test_eval_untouched.py
python tests/test_page_alignment.py
```
