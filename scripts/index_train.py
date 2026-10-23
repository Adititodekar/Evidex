"""
Index the entire Train corpus (35 PDFs) into the isolated named collection 'train'.
Extracts pages, structures, chunks, builds FAISS vectors, and BM25 index.
"""

import os
import sys
import time
import json
import logging
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from ingest.pdf_extract import extract_pdf_pages
from ingest.structure import build_structure_tree
from ingest.chunker import chunk_document
from ingest.cards import build_document_card
from ingest.siblings import detect_siblings, save_siblings
from ingest.index_build import build_collection_index, collection_exists

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("index_train")

def index_train_corpus():
    collection_name = "train"
    doc_dir = settings.DOCUMENTS_DIR
    logger.info(f"Indexing train corpus from {doc_dir} into collection '{collection_name}'...")

    if not os.path.exists(doc_dir):
        logger.error(f"Documents directory not found: {doc_dir}")
        return

    pdf_files = sorted([f for f in os.listdir(doc_dir) if f.lower().endswith(".pdf")])
    logger.info(f"Found {len(pdf_files)} PDF documents to process.")

    documents = []
    sections_by_doc = {}
    all_chunks = []
    total_pages = 0

    t_start = time.time()

    for idx, fname in enumerate(pdf_files, 1):
        pdf_path = os.path.join(doc_dir, fname)
        doc_id = fname
        doc_t0 = time.time()
        
        logger.info(f"[{idx}/{len(pdf_files)}] Processing {doc_id}...")

        # 1. Extract pages
        try:
            pages = extract_pdf_pages(pdf_path)
            total_pages += len(pages)
        except Exception as e:
            logger.error(f"Error extracting pages from {fname}: {e}")
            pages = []

        # 2. Extract structure
        try:
            sections = build_structure_tree(pdf_path, pages)
            sections_by_doc[doc_id] = sections
        except Exception as e:
            logger.error(f"Error extracting structure from {fname}: {e}")
            sections_by_doc[doc_id] = []
            sections = []

        # 3. Chunk document
        try:
            chunks = chunk_document(doc_id, pages, sections)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Error chunking {fname}: {e}")
            chunks = []

        # 4. Document Card
        try:
            card = build_document_card(pdf_path, collection_name=collection_name, force_refresh=False)
            card["total_pages"] = len(pages)
            card["chunk_count"] = len(chunks)
            documents.append(card)
        except Exception as e:
            logger.error(f"Error building card for {fname}: {e}")
            card = {
                "doc_id": doc_id,
                "entity": doc_id.replace(".pdf", ""),
                "doc_type": "report",
                "jurisdiction": "Unknown",
                "period": "Unknown",
                "status": "final",
                "scope_summary": "",
                "key_topics": [],
                "distinguishing_features": "",
                "total_pages": len(pages),
                "chunk_count": len(chunks)
            }
            documents.append(card)

        doc_dur = time.time() - doc_t0
        logger.info(f"[{idx}/{len(pdf_files)}] {doc_id}: {len(pages)} pages, {len(sections)} sections, {len(chunks)} chunks in {doc_dur:.2f}s")

    # 5. Build Sibling Table
    logger.info("Computing sibling clustering table across documents...")
    try:
        siblings_data = detect_siblings(documents)
        save_siblings(siblings_data, collection_name=collection_name)
        logger.info(f"Sibling table saved: {len(siblings_data)} sibling documents identified.")
    except Exception as e:
        logger.error(f"Error creating sibling table: {e}")

    # 6. Build Persistent FAISS & BM25 Indexes
    logger.info(f"Building FAISS vector index & BM25 index for {len(all_chunks)} chunks...")
    t_idx = time.time()
    res = build_collection_index(collection_name, documents, sections_by_doc, all_chunks)
    logger.info(f"Index built successfully in {time.time() - t_idx:.2f}s: {res}")

    total_time = time.time() - t_start
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print(f"Collection:      {collection_name}")
    print(f"Total Documents: {len(documents)}")
    print(f"Total Pages:     {total_pages}")
    print(f"Total Chunks:    {len(all_chunks)}")
    print(f"Total Elapsed:   {total_time:.2f}s ({total_time / 60:.2f} minutes)")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    index_train_corpus()
