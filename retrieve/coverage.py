"""
Step 5: Coverage Check & Adaptive Widening.
Deterministic guard ensuring evidence thresholds are met per breadth setting without unbounded loops.
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

MIN_BUDGETS = {
    "narrow": 10,
    "medium": 15,
    "broad": 22
}

MAX_BUDGETS = {
    "narrow": 18,
    "medium": 26,
    "broad": 40
}

def check_and_widen_coverage(
    candidate_chunks: List[Dict[str, Any]],
    surviving_docs: List[str],
    collection_index: Any,
    breadth: str = "medium"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Ensures minimum evidence budget is satisfied.
    If below threshold, deterministically widens page boundaries by +/- 2 pages.
    """
    logs = []
    min_needed = MIN_BUDGETS.get(breadth, 35)
    max_cap = MAX_BUDGETS.get(breadth, 150)

    curr_count = len(candidate_chunks)
    logs.append(f"Coverage check: {curr_count} chunks retrieved (min threshold: {min_needed}, max cap: {max_cap}).")

    if curr_count >= min_needed:
        # Cap to max budget if oversized
        return candidate_chunks[:max_cap], logs

    # Adaptive Widening: find pages currently covered and add adjacent pages
    covered_pages_by_doc: Dict[str, set] = {}
    for c in candidate_chunks:
        doc = c["document"]
        if doc not in covered_pages_by_doc:
            covered_pages_by_doc[doc] = set()
        covered_pages_by_doc[doc].add(c["page"])

    new_chunks_map = {c["chunk_id"]: c for c in candidate_chunks}
    
    # 1 widening round
    for doc_id, pages in covered_pages_by_doc.items():
        if len(new_chunks_map) >= min_needed:
            break
        min_p = max(1, min(pages) - 2)
        max_p = max(pages) + 2
        extra = collection_index.get_chunks_for_section(doc_id, min_p, max_p)
        for c in extra:
            new_chunks_map[c["chunk_id"]] = c

    logs.append(f"Widened coverage to {len(new_chunks_map)} chunks across neighboring pages.")
    final_list = list(new_chunks_map.values())
    return final_list[:max_cap], logs
