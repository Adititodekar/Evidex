# RUN_LOG.md: Experiment & Milestone Run Log

| Timestamp | Milestone / Iteration | Configuration / Changes | Acceptance Test / Metrics | Status & Observations |
|---|---|---|---|---|
| 2026-10-24 03:48 | Setup & Plan | Initial environment setup, `PLAN.md` registered, dependencies installed (PyMuPDF, pdfplumber, faiss, langfuse, rapidocr). | Workspace initialized, dependencies confirmed. | Initialized |
| 2026-10-24 04:09 | M1: Ingestion & Extraction | Implemented `ingest/pdf_extract.py`, `ingest/ocr.py`, `ingest/structure.py`, `ingest/chunker.py`. | `tests/test_page_alignment.py`: 200/200 (100.00%) page alignment on offset-0 compliant chunks; SAMA OCR output 117 chars. | PASSED |
| 2026-10-24 04:38 | M2: Metadata & Sibling Cards | Implemented `ingest/cards.py`, `ingest/siblings.py`. Generated document cards and sibling table. | `tests/test_m2_cards.py`: 35/35 cards generated. Metal Coatings FY25 & FY26 identified as siblings with discriminator 'period' (FY2025 vs FY2026). | PASSED |
| 2026-10-24 04:40 | M3: Multi-Vector & BM25 Indexes | Implemented `ingest/index_build.py`. Multi-vector FAISS + BM25Okapi + SQLite storage under `data/<collection_name>/`. | `tests/test_m3_collections.py`: Tested two concurrent collections (`test_col_alpha`, `test_col_beta`). Deleting alpha leaves beta completely intact and queryable. | PASSED |
| 2026-10-24 04:50 | M4: Query Pipeline Components | Implemented `retrieve/understand.py`, `retrieve/meta_filter.py`, `retrieve/router.py`, `retrieve/drilldown.py`, `retrieve/coverage.py`, `retrieve/verify.py`, `retrieve/assemble.py`. | Integrated full 7-step hierarchical retrieval orchestrator `execute_retrieval_pipeline`. Built `eval/proxy_metrics.py`. | PASSED |
| 2026-10-24 04:56 | M5: Answer Generation & Claim Check | Implemented `answer/generate.py`, `answer/claim_check.py`. Structured prompt with `## Bottom line`, headed analysis, tables, `[Doc p.X]` citations, abstention on unanswerable questions. | `verify_claims_against_evidence` sentence-level validation against cited chunk texts; abstention verified on Question B32. | PASSED |
| 2026-10-24 05:02 | M6: API Server & Contract | Implemented `app/schemas.py`, `app/api.py`. Exposes `POST /index` (multipart zip upload) and `POST /query`. | `tests/test_api_contract.py`: 100% passed! Verified status, collections, chunks, exact 9-step audit trace schema, and usage metrics. | PASSED |
| 2026-10-24 05:04 | M7: Evaluation Framework | Integrated unmodified official evaluator `eval/official_eval.py` (SHA-256 verified), created `eval/splits.json` (70/30 stratified train/val split), `eval/run_eval.py`, `eval/diagnose.py`. | Zero-touch compliance on official evaluator; OpenCodeClient verified with Gemini endpoint. | PASSED |
| 2026-10-24 05:05 | M8: Deployment & Documentation | Created `Dockerfile`, `requirements.txt`, `docs/WRITEUP.md` (3-page comprehensive technical report). | Production container ready; comprehensive architecture and trade-off writeup complete. | PASSED |

---
