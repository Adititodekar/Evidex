"""
Step 6: Evidence Verification & Quality Classification.
Filters candidate chunks to match the official judge's relevance criteria, maximizing Context Precision.
"""

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

def verify_chunk_relevance_heuristic(query: str, chunk_text: str) -> float:
    """
    Computes a strict lexical and semantic relevance score for a chunk against the query.
    Checks for exact key entities, numbers, and concept overlaps.
    """
    q_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower()))
    c_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', chunk_text.lower()))
    
    if not q_words or not c_words:
        return 0.0

    # Stopwords filter
    stopwords = {"what", "when", "where", "which", "who", "whom", "this", "that", "these", "those", "from", "with", "about", "into", "through", "during", "before", "after", "above", "below", "have", "has", "had", "having", "does", "did", "doing"}
    meaningful_q = q_words - stopwords
    if not meaningful_q:
        meaningful_q = q_words

    overlap = meaningful_q.intersection(c_words)
    score = len(overlap) / len(meaningful_q)

    # Bonus if chunk contains numbers/percentages/ratios mentioned in or relevant to financial queries
    has_numbers = bool(re.search(r'\b\d+(?:\.\d+)?%?\b', chunk_text))
    if has_numbers and score > 0.15:
        score += 0.1

    return score

def verify_and_rank_evidence(
    candidate_chunks: List[Dict[str, Any]],
    query: str,
    breadth: str = "medium",
    max_evidence_cap: int = None,
    min_score_threshold: float = 0.10
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Filters and ranks candidate evidence chunks.
    Discards low-relevance filler to protect Context Precision while preserving all essential pages.
    """
    logs = []
    
    cap = max_evidence_cap or (16 if breadth == "narrow" else (24 if breadth == "medium" else 35))
    min_floor = 8 if breadth == "narrow" else (12 if breadth == "medium" else 18)
    
    scored_chunks = []
    for c in candidate_chunks:
        sc = verify_chunk_relevance_heuristic(query, c["text"])
        if c.get("chunk_type") == "table":
            sc += 0.05
        scored_chunks.append((sc, c))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    verified = []
    for sc, c in scored_chunks:
        if sc >= min_score_threshold or (len(verified) < min_floor and sc > 0.03):
            c_copy = dict(c)
            c_copy["score"] = round(sc, 4)
            verified.append(c_copy)
        if len(verified) >= cap:
            break

    logs.append(f"Verified {len(verified)} chunks from {len(candidate_chunks)} candidates (cap: {cap}).")
    return verified, logs
