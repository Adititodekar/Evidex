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

    # Determine top-k per facet based on breadth
    top_k_per_facet = 15 if breadth == "broad" else (8 if breadth == "medium" else 5)
    
    # 2. Targeted Multi-Facet BM25 & Vector Retrieval
    facet_hit_ids = set()
    for q_text in search_queries:
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

    # 3. Contiguous Window Expansion (+/- 1 page) for Top Hit Pages
    hit_pages_by_doc: Dict[str, list] = {}
    for c in candidate_chunks_map.values():
        doc = c.get("document", c.get("doc_id", ""))
        p = c.get("page", 0)
        if doc not in hit_pages_by_doc:
            hit_pages_by_doc[doc] = []
        if p not in hit_pages_by_doc[doc]:
            hit_pages_by_doc[doc].append(p)

    for doc_id, pages in hit_pages_by_doc.items():
        # Focus on top 6 hit pages per document to avoid flooding the pool
        for p in pages[:6]:
            for ep in (max(1, p - 1), p + 1):
                extra = collection_index.get_chunks_for_section(doc_id, ep, ep)
                for ec in extra:
                    candidate_chunks_map[ec["chunk_id"]] = ec

    # 4. Leaf Section Retrieval for concise sections
    for doc_id, sections in selected_sections_by_doc.items():
        for sec in sections[:2]:
            start_p = sec["start_page"]
            end_p = sec["end_page"]
            if (end_p - start_p) <= 8:
                sec_chunks = collection_index.get_chunks_for_section(doc_id, start_p, end_p)
                for c in sec_chunks:
                    candidate_chunks_map[c["chunk_id"]] = c

    # 5. Score all candidates against query and sort descending
    candidates = list(candidate_chunks_map.values())
    scored = []
    for c in candidates:
        sc = verify_chunk_relevance_heuristic(query, c.get("text", ""))
        scored.append((sc, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]
