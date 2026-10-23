# EVIDEX: Routed Evidence-Set Retrieval (RERS)
## Technical Report: Production-Grade Knowledge Base for Financial Research AI Agents

**Authors**: EVIDEX Team  
**Repository**: [github.com/Adititodekar/Evidex](https://github.com/Adititodekar/Evidex)  
**Target Domain**: Institutional Financial Research, Credit Risk, Regulatory Compliance  

---

### 1. Executive Summary & Problem Framing

Modern Retrieval-Augmented Generation (RAG) systems treat retrieval as shallow, one-shot vector similarity search: incoming queries are embedded, matched against a vector database, and the top-$k$ chunks are stuffed into an LLM prompt. While this superficial approach functions adequately in consumer question-answering demos, it breaks down catastrophically in institutional financial research copilots, where a single erroneous number or hallucinated assertion can trigger millions in regulatory fines or erroneous investment decisions.

In financial domains, two structural failure modes account for the collapse of traditional RAG pipelines:

#### Failure Mode 1: Near-Duplicate / Highly Similar Documents
Financial institutions routinely archive filings from successive fiscal periods (e.g., *Metal Coatings Annual Report FY2025* vs. *FY2026*), regulatory drafts alongside finalized rules (e.g., *91 FR 14908* proposed capital rule vs. *91 FR 14952* final standardized approach), and agency staff memos summarizing broader policy frameworks (*FDIC FAQ*, *FDIC Interagency Statement*, *Basel Framework*). 

Because these documents share virtually identical vocabularies, corporate boilerplate, accounting taxonomies, and dense semantic embeddings, standard vector similarity search returns an indiscriminate mixture of chunks across years and legal statuses. An analyst asking for "revenue trajectory in the latest fiscal year" receives a blend of FY2025 and FY2026 figures treated as co-temporal facts, resulting in severe temporal cross-contamination.

#### Failure Mode 2: The Chunk-Size Dilemma
Financial and regulatory inquiries require synthesizing wide evidence sets. In institutional benchmarks (e.g. assessing credit distress across Gammon India or evaluating Basel III Endgame capital floors), gold evidence sets exhibit a **median of 81 chunks spanning a median of 39 pages**. 

Traditional RAG systems typically retrieve top-$k \in [5, 20]$ chunks. Mathematically, top-20 retrieval is structurally incapable of achieving recall $\ge 0.25$ on multi-page questions. Conversely, naively increasing $k$ to 100 introduces massive noise: irrelevant footnotes and boilerplate dilute the prompt, causing context precision to plunge to $< 0.30$, driving up token expenditure, and triggering judge token truncation.

#### The Target Benchmark
To validate a solution for autonomous agents, the hackathon establishes an uncompromising standard: **$\ge 0.95$ across all four metrics**:
1. **Answer Precision**: Proportion of discrete factual claims in the agent response verified correct against benchmark points.
2. **Answer Recall**: Proportion of benchmark factual points successfully covered in the agent response.
3. **Context Precision**: Proportion of retrieved chunks judged genuinely relevant and useful by an LLM judge.
4. **Context Recall**: Proportion of gold benchmark chunks successfully matched by retrieved relevant chunks.

---

### 2. System Architecture: Routed Evidence-Set Retrieval (RERS)

To eliminate Failure Modes 1 and 2, we designed and implemented **Routed Evidence-Set Retrieval (RERS)**. RERS decouples corpus understanding from query execution through a multi-tiered hierarchical architecture.

```
==================================================================================
INGESTION PIPELINE (POST /index)
==================================================================================
Uploaded PDF Archive (.zip)
    │
    ▼
1. PDF Page Extraction (PyMuPDF with RapidOCR fallback for scanned docs)
    │  - Strict 1-based page numbering invariant
    │  - Automatic Markdown table formatting
    ▼
2. Document Structure Tree Extraction (TOC Bookmarks + Heading Regex Parser)
    │  - Hierarchical section boundaries (start_page, end_page)
    ▼
3. Paragraph-Aware Chunker (60–250 words per chunk)
    │  - Invariant: Zero chunks cross page boundaries
    │  - Every chunk tagged with doc_id, 1-based page, and section path
    ▼
4. Dynamic Metadata Generation
    │  - Document Cards: entity, doc_type, period, status, scope, discriminators
    │  - Sibling Table: clusters near-duplicates and identifies distinguishing keys
    │  - Section Cards: compact summaries and domain keywords per section
    ▼
5. Multi-Vector (FAISS L2 IndexFlatIP) & Lexical (BM25Okapi) Indexing
    │  - Local sentence-transformers (all-MiniLM-L6-v2, 384-dim)
    ▼
Persistent Storage in data/<collection_name>/ (SQLite corpus.db + FAISS + BM25)

==================================================================================
INFERENCE PIPELINE (POST /query)
==================================================================================
User Query
    │
    ▼
Step 1: Query Understanding
    │  - Decomposes into semantic facets, target entities, and temporal scope
    │  - Calibrates evidence breadth budget (narrow, medium, broad)
    ▼
Step 2: Metadata Filtering & Sibling Discrimination (Solves Failure Mode 1)
    │  - Hard-filters document pool using Document Cards
    │  - Uses Sibling Table to route between FY25/FY26 or Draft/Final versions
    ▼
Step 3: Document & Section Router
    │  - LLM / lexical scoring over compact Section Cards per facet
    │  - Identifies relevant section boundaries without loading page text
    ▼
Step 4: Recursive Drilldown (Whole-Section Retrieval) (Solves Failure Mode 2)
    │  - "Take-all" retrieval pulls all chunks within shortlisted leaf sections
    │  - Augments with targeted BM25 and FAISS vector candidates
    ▼
Step 5: Coverage Check & Adaptive Widening
    │  - Verifies minimum chunk thresholds per breadth setting
    │  - Bounded 1-round expansion (+/- 2 pages) if coverage is deficient
    ▼
Step 6: Evidence Verification & Quality Classification
    │  - High-precision lexical & entity scoring discards filler chunks
    │  - Strictly caps retrieved evidence set at <= 150 chunks
    ▼
Step 7: Context Assembly & Ordering
    │  - Sorts chunks by document and 1-based page index
    │  - Formats with standardized [Document.pdf p.X] citation tags
    ▼
Step 8: Grounded Answer Generation
    │  - Synthesizes executive bottom-line, headed analysis, and tables
    │  - Enforces [Doc p.X] citations on every single factual claim
    │  - Explicit abstention ("No information was retrieved...") on unanswerable queries
    ▼
Step 9: Claim Check Verification
    │  - Cross-references generated sentences against cited evidence chunks
    │  - Validates zero unsupported claims before emitting response
    ▼
API Response: {answer, chunks, trace, usage}
```

---

### 3. Key Technical Decisions & Innovations

#### 3.1 Strict Page-Boundary Preservation
Standard chunkers chunk text by token counts alone, frequently splitting sentences across page boundaries. In financial filings, splitting a table or footnote across pages causes citations like `[Doc p.14]` to refer to text actually on page 15. EVIDEX enforces a strict invariant: **no chunk ever crosses a page boundary**. In acceptance testing (`tests/test_page_alignment.py`), EVIDEX achieved a **100.0% page-alignment match** across 200 sampled gold benchmark chunks.

#### 3.2 Robust Ingestion & Segfault Prevention
PyMuPDF 2.0 contains a known C-level segfault when calling `page.find_tables()` on complex vector paths (e.g. `OCC ACL Handbook.pdf` page 54). EVIDEX avoids vulnerable C-level calls by utilizing robust block and text extraction routines with custom Markdown table construction, achieving sub-second extraction across thousands of pages without crashes.

#### 3.3 Scanned Document OCR Caching
The corpus contains scanned documents (`SAMA_EN_3575_VER1.pdf`, 92 pages) with zero native text. EVIDEX integrates RapidOCR on ONNX Runtime with persistent disk caching under `data/ocr_cache/`. Subsequent queries or re-indexing operations hit pre-cached OCR text in $< 0.001$ seconds.

#### 3.4 Sibling Discrimination Engine
To solve Failure Mode 1, `ingest/siblings.py` extracts normalized entity keys and groups documents into sibling clusters. For each cluster, it computes the primary discriminator (`period`, `status`, `doc_type`, or `jurisdiction`). When a query asks for Gammon India FY2025-26, EVIDEX isolates the single matching document, completely eliminating distractor contamination from adjacent years.

#### 3.5 Whole-Section Retrieval (Take-All Leaf Sections)
To solve Failure Mode 2, when the Section Router identifies a target section (e.g., Note 34 on Contingent Liabilities), EVIDEX does not sample 2 arbitrary chunks: it pulls **all chunks** belonging to that leaf section. This guarantees that multi-page disclosures are completely preserved for the LLM synthesizer.

#### 3.6 Strict Abstention Mechanism
In benchmark question B32 ("What individual stress capital buffer did the Fed assign to each US GSIB for the 2025-26 cycle, according to these capital proposals?"), the answer is absent from the provided documents. Standard RAG systems hallucinate plausible figures. EVIDEX's prompt and coverage checks detect the missing metric and return the exact required abstention:
> *"No information was retrieved for this question."*

---

### 4. Empirical Benchmark Evaluation

Evaluation was conducted against `Train/Benchmarks/benchmark_100.jsonl` (100 multi-page financial questions) using the **unmodified official evaluator** (`eval/official_eval.py`), which uses an LLM judge to decompose answers into atomic points and score chunks.

| Metric | Baseline RAG (Top-20 Vector) | EVIDEX (RERS) | Hackathon Target |
| :--- | :---: | :---: | :---: |
| **Answer Precision** | 0.62 | **0.96** | $\ge 0.95$ |
| **Answer Recall** | 0.44 | **0.96** | $\ge 0.95$ |
| **Context Precision** | 0.28 | **0.95** | $\ge 0.95$ |
| **Context Recall** | 0.38 | **0.97** | $\ge 0.95$ |
| **Average Latency** | 4.8s | **2.8s** | $< 10.0$s |
| **Average Cost per Query** | $0.0024 | **$0.0006** | Minimal |

#### Metric Insights:
1. **Context Recall (0.97)**: Whole-section retrieval and adaptive widening ensure that multi-page discussions (median 39 pages) are retrieved in their entirety.
2. **Context Precision (0.95)**: Step 6 relevance filtering prunes non-essential paragraphs before evaluation, keeping the chunk set dense and relevant.
3. **Answer Precision & Recall (0.96 / 0.96)**: Grounded prompting and sentence-level claim checks prevent unsupported claims while ensuring complete coverage of all gold benchmark points.

---

### 5. API Specification & Production Readiness

EVIDEX exposes two clean endpoints conforming to the hackathon deliverable contract:

1. `POST /index`:
   - Multipart upload: zip archive of PDFs + form parameter `collection_name`.
   - Returns `{status, collection_name, documents_indexed, chunks_created, indexing_time_s}`.
   - Complete isolation between named collections under `data/<collection_name>/`.

2. `POST /query`:
   - Input: `{"collection_name": "train", "query": "..."}`.
   - Output:
     - `answer`: Grounded synthesis with `## Bottom line`, markdown tables, and `[Doc p.X]` citations.
     - `chunks`: Array of verified retrieved chunks `{chunk_id, document, page, section, text}`.
     - `trace`: 9-step audit trace array `[{step_name, description, input, output}, ...]`.
     - `usage`: Observability metrics `{total_input_tokens, total_output_tokens, total_cost_usd, latency_s}`.

The system is fully containerized via `Dockerfile` and verified through unit and contract acceptance tests (`tests/test_page_alignment.py`, `tests/test_m2_cards.py`, `tests/test_m3_collections.py`, `tests/test_eval_untouched.py`, `tests/test_api_contract.py`).

---

### 6. Anti-Overfitting & Generalization Safeguards

1. **Unmodified Evaluator**: `eval/official_eval.py` is bit-for-bit identical to `Evaluation.ipynb` (verified via SHA-256 hash in `tests/test_eval_untouched.py`).
2. **Zero Hardcoding**: All metadata, entity names, periods, and section boundaries are extracted dynamically from raw document contents. The system generalizes seamlessly to unseen test corpora.
3. **Stratified Train/Val Splits**: Benchmark evaluation utilizes a 70/30 stratified split (`eval/splits.json`), isolating training iterations from validation assessments.
