"""
FastAPI Server for EVIDEX: Routed Evidence-Set Retrieval (RERS).
Implements POST /index and POST /query adhering to the exact hackathon API specification.
"""

import os
import sys
import time
import json
import zipfile
import shutil
import logging
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import IndexResponse, QueryRequest, QueryResponse, RetrievedChunk, TraceStep, UsageMetrics
from ingest.pdf_extract import extract_pdf_pages
from ingest.structure import build_structure_tree
from ingest.chunker import chunk_document
from ingest.cards import build_document_card
from ingest.siblings import detect_siblings, save_siblings
from ingest.index_build import build_collection_index, collection_exists, get_collection_dir, CollectionIndex
from retrieve.assemble import execute_retrieval_pipeline
from answer.generate import generate_answer
from answer.claim_check import verify_claims_against_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evidex_api")

app = FastAPI(
    title="EVIDEX: Routed Evidence-Set Retrieval (RERS)",
    description="High-precision financial research knowledge engine for autonomous AI agents.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "EVIDEX RERS"}

@app.post("/index", response_model=IndexResponse)
def index_documents(
    file: UploadFile = File(..., description="A zip archive containing PDF documents to index"),
    collection_name: str = Form(..., description="Unique name for this isolated document collection")
):
    """
    Ingests, extracts, structures, and indexes a collection of PDF documents from an uploaded zip.
    """
    t0 = time.time()
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip archive.")

    target_dir = get_collection_dir(collection_name)
    raw_docs_dir = os.path.join(target_dir, "raw_docs")
    os.makedirs(raw_docs_dir, exist_ok=True)

    zip_path = os.path.join(target_dir, "upload.zip")
    try:
        with open(zip_path, "wb") as f:
            content = file.file.read()
            f.write(content)

        # Unzip safely (avoid zip slip)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                filename = os.path.basename(member)
                if not filename or not filename.lower().endswith(".pdf"):
                    continue
                source = zip_ref.open(member)
                target = open(os.path.join(raw_docs_dir, filename), "wb")
                with source, target:
                    shutil.copyfileobj(source, target)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract zip file: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

    pdf_files = sorted([f for f in os.listdir(raw_docs_dir) if f.lower().endswith(".pdf")])
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files found inside the uploaded zip.")

    documents = []
    sections_by_doc = {}
    all_chunks = []

    for fname in pdf_files:
        pdf_path = os.path.join(raw_docs_dir, fname)
        doc_id = fname

        pages = extract_pdf_pages(pdf_path)
        sections = build_structure_tree(pdf_path, pages)
        sections_by_doc[doc_id] = sections
        chunks = chunk_document(doc_id, pages, sections)
        all_chunks.extend(chunks)

        card = build_document_card(pdf_path, collection_name=collection_name, force_refresh=False)
        card["total_pages"] = len(pages)
        card["chunk_count"] = len(chunks)
        documents.append(card)

    siblings_data = detect_siblings(documents)
    save_siblings(siblings_data, collection_name=collection_name)

    build_collection_index(collection_name, documents, sections_by_doc, all_chunks)
    elapsed = round(time.time() - t0, 2)

    return IndexResponse(
        status="success",
        collection_name=collection_name,
        documents_indexed=len(documents),
        chunks_created=len(all_chunks),
        indexing_time_s=elapsed,
        message=f"Successfully indexed {len(documents)} documents ({len(all_chunks)} chunks) in {elapsed}s."
    )

@app.post("/query", response_model=QueryResponse)
def query_collection(req: QueryRequest):
    """
    Executes Routed Evidence-Set Retrieval (RERS) and generates an authoritative grounded answer.
    """
    t0 = time.time()
    col = req.collection_name
    query = req.query.strip()

    if not collection_exists(col):
        raise HTTPException(status_code=404, detail=f"Collection '{col}' does not exist.")

    # Load collection index and siblings table
    col_idx = CollectionIndex(col)
    col_dir = get_collection_dir(col)
    siblings_path = os.path.join(col_dir, "siblings.json")
    sibling_table = {}
    if os.path.exists(siblings_path):
        with open(siblings_path, "r", encoding="utf-8") as f:
            sibling_table = json.load(f)

    # Execute 7-step retrieval pipeline
    verified_chunks, raw_trace, context_str = execute_retrieval_pipeline(query, col_idx, sibling_table)

    trace: List[TraceStep] = []
    for step in raw_trace:
        trace.append(TraceStep(
            step_name=step["step_name"],
            description=step["description"],
            input=step.get("input", {}),
            output=step.get("output", {})
        ))

    total_in_tokens = 0
    total_out_tokens = 0
    total_cost = 0.0

    # Step 8: Answer Generation
    answer_text, usage_ans = generate_answer(query, context_str)
    total_in_tokens += usage_ans.get("input_tokens", 0)
    total_out_tokens += usage_ans.get("output_tokens", 0)
    total_cost += usage_ans.get("cost_usd", 0.0)

    trace.append(TraceStep(
        step_name="llm_answer_generation",
        description="Synthesized verified evidence into an institutional answer with strict inline citations",
        input={"context_length_chars": len(context_str)},
        output={"answer_length_chars": len(answer_text), "cost_usd": usage_ans.get("cost_usd", 0.0)}
    ))

    # Step 9: Claim Verification
    claim_check_res = verify_claims_against_evidence(answer_text, verified_chunks)
    trace.append(TraceStep(
        step_name="claim_check",
        description="Verified sentence-level claims against cited evidence chunks",
        input={"citations_found": claim_check_res.get("citations_found", 0)},
        output={
            "citations_valid": claim_check_res.get("citations_valid", 0),
            "valid_citation_ratio": claim_check_res.get("valid_citation_ratio", 1.0),
            "is_valid": claim_check_res.get("is_valid", True)
        }
    ))

    elapsed = round(time.time() - t0, 3)
    response_chunks = [
        RetrievedChunk(
            chunk_id=c.get("chunk_id", ""),
            document=c.get("document", c.get("doc_id", "")),
            page=c.get("page", 0),
            section=c.get("section", ""),
            chunk_type=c.get("chunk_type", "text"),
            text=c.get("text", ""),
            word_count=c.get("word_count", 0)
        )
        for c in verified_chunks
    ]

    usage_metrics = UsageMetrics(
        total_input_tokens=total_in_tokens,
        total_output_tokens=total_out_tokens,
        total_cost_usd=round(total_cost, 6),
        latency_s=elapsed
    )

    return QueryResponse(
        answer=answer_text,
        chunks=response_chunks,
        trace=trace,
        usage=usage_metrics
    )
