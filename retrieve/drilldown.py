import re
import logging
from typing import Dict, Any, List

from retrieve.verify import verify_chunk_relevance_heuristic

logger = logging.getLogger(__name__)

def drilldown_evidence_set(
    selected_sections_by_doc: Dict[str, List[Dict[str, Any]]],
    query: str,
    surviving_docs: List[str],
    collection_index: Any,
    breadth: str = "medium",
    facets: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves evidence chunks via facet-guided multi-vector & BM25 round-robin,
    augmented with surrounding window expansion and targeted leaf sections.
    """
    candidate_chunks_map: Dict[str, Dict[str, Any]] = {}

    # 1. Collect Search Facets
    search_queries = [query]
    if facets:
        for f in facets:
            need = f.get("need", "")
            if need and need not in search_queries:
                search_queries.append(need)

    # Add entity-stripped clean query for focused keyword / ratio matching
    clean_kw_query = query
    for doc in surviving_docs:
        doc_base = re.sub(r'\.pdf$', '', doc, flags=re.IGNORECASE).replace('_', ' ').replace('-', ' ')
        for token in doc_base.split():
            if len(token) > 2:
                clean_kw_query = re.sub(rf'\b{re.escape(token)}\b', '', clean_kw_query, flags=re.IGNORECASE)

    clean_kw_query = re.sub(r'\b(what|when|where|which|who|whom|why|how|was|is|are|the|end|of|in|at|for|fy\s*20\d{2}|20\d{2})\b', '', clean_kw_query, flags=re.IGNORECASE)
    clean_kw_query = re.sub(r'\s+', ' ', clean_kw_query).strip()
    if clean_kw_query and len(clean_kw_query) > 3 and clean_kw_query not in search_queries:
        search_queries.append(clean_kw_query)

    # Determine top-k per facet based on breadth
    top_k_per_facet = 80 if breadth == "broad" else (45 if breadth == "medium" else 30)
    
    # 2. Targeted Multi-Facet BM25 & Vector Retrieval (with balanced multi-doc allocation)
    facet_hit_ids = set()
    for q_text in search_queries:
        if len(surviving_docs) > 1 and len(surviving_docs) <= 8:
            # Multi-document comparison: ensure proportional representation across every entity
            per_doc_k = max(15, (top_k_per_facet // len(surviving_docs)) + 6)
            for s_doc in surviving_docs:
                v_hits = collection_index.search_vectors(q_text, top_k=per_doc_k, filter_docs=[s_doc])
                b_hits = collection_index.search_bm25(q_text, top_k=per_doc_k, filter_docs=[s_doc])
                for cid, _ in v_hits:
                    facet_hit_ids.add(cid)
                for cid, _ in b_hits:
                    facet_hit_ids.add(cid)
        else:
            v_hits = collection_index.search_vectors(q_text, top_k=top_k_per_facet, filter_docs=surviving_docs)
            b_hits = collection_index.search_bm25(q_text, top_k=top_k_per_facet, filter_docs=surviving_docs)
            for cid, _ in v_hits:
                facet_hit_ids.add(cid)
            for cid, _ in b_hits:
                facet_hit_ids.add(cid)

    # Batch fetch retrieved chunks
    if facet_hit_ids:
        retrieved = collection_index.get_chunks_by_ids(list(facet_hit_ids))
        for c in retrieved:
            candidate_chunks_map[c["chunk_id"]] = c

    # 3. Whole Leaf Section Retrieval for all routed sections
    for doc_id, sections in selected_sections_by_doc.items():
        for sec in sections:
            start_p = sec.get("start_page", 1)
            end_p = sec.get("end_page", start_p)
            span = end_p - start_p
            if span <= 30:
                sec_chunks = collection_index.get_chunks_for_section(doc_id, start_p, end_p)
                for c in sec_chunks:
                    candidate_chunks_map[c["chunk_id"]] = c
            else:
                # For large chapters, retrieve first 25 pages (reports/audits) + distributed coverage
                sec_chunks = collection_index.get_chunks_for_section(doc_id, start_p, start_p + 25)
                for c in sec_chunks:
                    candidate_chunks_map[c["chunk_id"]] = c
                if breadth == "broad":
                    mid_p = (start_p + end_p) // 2
                    mid_chunks = collection_index.get_chunks_for_section(doc_id, max(start_p, mid_p - 10), min(end_p, mid_p + 10))
                    for c in mid_chunks:
                        candidate_chunks_map[c["chunk_id"]] = c
                    end_chunks = collection_index.get_chunks_for_section(doc_id, max(start_p, end_p - 15), end_p)
                    for c in end_chunks:
                        candidate_chunks_map[c["chunk_id"]] = c

    # 4. Score all candidates against query and sort descending
    candidates = list(candidate_chunks_map.values())
    scored = []
    for c in candidates:
        sc = verify_chunk_relevance_heuristic(query, c.get("text", ""))
        scored.append((sc, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]
