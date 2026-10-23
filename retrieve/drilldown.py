"""
Step 4: Recursive Drilldown and Whole-Section Retrieval.
Solves Failure Mode 2: Takes entire leaf sections to guarantee complete coverage across multi-page sections.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def drilldown_evidence_set(
    selected_sections_by_doc: Dict[str, List[Dict[str, Any]]],
    query: str,
    surviving_docs: List[str],
    collection_index: Any,
    breadth: str = "medium"
) -> List[Dict[str, Any]]:
    """
    Retrieves all chunks from selected leaf sections, augmented with top BM25 and Vector hits.
    Guarantees that entire multi-page discussions are pulled as complete evidence sets.
    """
    candidate_chunks_map: Dict[str, Dict[str, Any]] = {}

    # 1. Whole-Section Retrieval (Failure Mode 2 solution)
    for doc_id, sections in selected_sections_by_doc.items():
        for sec in sections:
            start_p = sec["start_page"]
            end_p = sec["end_page"]
            sec_chunks = collection_index.get_chunks_for_section(doc_id, start_p, end_p)
            for c in sec_chunks:
                candidate_chunks_map[c["chunk_id"]] = c

    # 2. Targeted BM25 & Vector Candidate Retrieval from surviving documents
    top_k_vector = 40 if breadth == "broad" else (25 if breadth == "medium" else 15)
    top_k_bm25 = 40 if breadth == "broad" else (25 if breadth == "medium" else 15)

    vec_hits = collection_index.search_vectors(query, top_k=top_k_vector, filter_docs=surviving_docs)
    vec_chunk_ids = [cid for cid, _ in vec_hits]
    vec_chunks = collection_index.get_chunks_by_ids(vec_chunk_ids)
    for c in vec_chunks:
        candidate_chunks_map[c["chunk_id"]] = c

    bm25_hits = collection_index.search_bm25(query, top_k=top_k_bm25, filter_docs=surviving_docs)
    bm25_chunk_ids = [cid for cid, _ in bm25_hits]
    bm25_chunks = collection_index.get_chunks_by_ids(bm25_chunk_ids)
    for c in bm25_chunks:
        candidate_chunks_map[c["chunk_id"]] = c

    return list(candidate_chunks_map.values())
