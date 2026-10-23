"""
Step 3: Document & Section Router.
Navigates section cards hierarchically per facet without loading raw page texts.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def score_section(section: Dict[str, Any], facet_need: str) -> float:
    """Computes lexical and keyword overlap score between section card and facet need."""
    need_tokens = set(re.findall(r'\b\w{3,}\b', facet_need.lower()))
    if not need_tokens:
        return 0.0

    score = 0.0
    title_tokens = set(re.findall(r'\b\w{3,}\b', section.get("title", "").lower()))
    keywords = set([k.lower() for k in section.get("keywords", [])])
    summary_tokens = set(re.findall(r'\b\w{3,}\b', section.get("summary", "").lower()))

    # Title matches carry highest weight
    title_matches = len(need_tokens.intersection(title_tokens))
    score += title_matches * 3.0

    # Keyword matches
    kw_matches = len(need_tokens.intersection(keywords))
    score += kw_matches * 2.0

    # Summary matches
    summ_matches = len(need_tokens.intersection(summary_tokens))
    score += summ_matches * 1.0

    return score

def route_sections_for_facets(
    facets: List[Dict[str, Any]],
    surviving_docs: List[str],
    collection_index: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    For each surviving document, scores and selects the top sections relevant to query facets.
    Returns: {doc_id: [selected_section_dict, ...]}
    """
    selected_sections_by_doc: Dict[str, List[Dict[str, Any]]] = {}

    for doc_id in surviving_docs:
        sections = collection_index.get_sections_for_doc(doc_id)
        if not sections:
            continue

        scored_sections = []
        for sec in sections:
            best_score = 0.0
            for f in facets:
                sc = score_section(sec, f.get("need", ""))
                if sc > best_score:
                    best_score = sc
            scored_sections.append((best_score, sec))

        scored_sections.sort(key=lambda x: x[0], reverse=True)

        # Select top sections (or all sections if small document <= 3 sections)
        if len(sections) <= 3:
            chosen = sections
        else:
            # Pick top 2-4 scoring sections, plus any section with positive score
            chosen = [sec for score, sec in scored_sections if score > 0][:4]
            if not chosen:
                # If no positive lexical match, take first 2 sections (often executive overview)
                chosen = [s for _, s in scored_sections[:2]]

        selected_sections_by_doc[doc_id] = chosen

    return selected_sections_by_doc
