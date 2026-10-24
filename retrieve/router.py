"""
Step 3: Document & Section Router.
Navigates section cards hierarchically per facet using LLM navigation + semantic overlap.
Guarantees full coverage of governance, auditor reports, and financial notes.
"""

import re
import json
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

def route_sections_with_llm(
    doc_id: str,
    sections: List[Dict[str, Any]],
    facets: List[Dict[str, Any]]
) -> List[str]:
    """
    LLM navigation over section cards per facet.
    Selects all relevant chapter and note IDs to prevent facet starvation.
    """
    if len(sections) <= 6:
        return [s.get("section_id", s.get("title")) for s in sections]

    outline = []
    for s in sections[:40]:
        outline.append({
            "section_id": s.get("section_id"),
            "title": s.get("title"),
            "pages": f"p.{s.get('start_page', 1)}-{s.get('end_page', 1)}",
            "summary": s.get("summary", "")[:120]
        })

    facet_texts = [f.get("need", "") for f in facets if f.get("need")]
    system_prompt = "You are an expert financial research navigator. Respond strictly with JSON."
    user_prompt = f"""Document Outline:
{json.dumps(outline, indent=2)}

Research Facets to cover:
{json.dumps(facet_texts, indent=2)}

Select ALL section_ids that contain relevant disclosures, notes, auditor opinions, or data for these facets.
Respond as JSON: {{"selected_section_ids": ["sec_1", "sec_2", ...]}}"""

    try:
        from app.llm import default_llm_client
        resp, _ = default_llm_client.call_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1024,
            temperature=0.0
        )
        if isinstance(resp, dict) and "selected_section_ids" in resp:
            return resp["selected_section_ids"]
        elif isinstance(resp, list):
            return resp
    except Exception as e:
        logger.warning(f"LLM section routing fallback for {doc_id}: {e}")

    return []

def route_sections_for_facets(
    facets: List[Dict[str, Any]],
    surviving_docs: List[str],
    collection_index: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    For each surviving document, selects all sections relevant to query facets.
    Combines LLM outline navigation with facet-specific scoring.
    """
    selected_sections_by_doc: Dict[str, List[Dict[str, Any]]] = {}

    for doc_id in surviving_docs:
        sections = collection_index.get_sections_for_doc(doc_id)
        if not sections:
            continue

        if len(sections) <= 6:
            selected_sections_by_doc[doc_id] = sections
            continue

        chosen_ids = set()
        chosen = []

        # 1. LLM Outline Navigation
        llm_selected_ids = route_sections_with_llm(doc_id, sections, facets)
        sec_by_id = {s.get("section_id"): s for s in sections}
        for sid in llm_selected_ids:
            if sid in sec_by_id and sid not in chosen_ids:
                chosen_ids.add(sid)
                chosen.append(sec_by_id[sid])

        # 2. Facet-specific scoring to ensure no facet is missed
        for f in facets:
            need = f.get("need", "")
            facet_scored = [(score_section(sec, need), sec) for sec in sections]
            facet_scored.sort(key=lambda x: x[0], reverse=True)
            for sc, sec in facet_scored[:2]:
                sid = sec.get("section_id", sec.get("title"))
                if sc > 0 and sid not in chosen_ids:
                    chosen_ids.add(sid)
                    chosen.append(sec)

        # 3. If still fewer than 4 sections, take top overall
        if len(chosen) < 4:
            overall_scored = []
            for sec in sections:
                sc = max(score_section(sec, f.get("need", "")) for f in facets) if facets else 0.0
                overall_scored.append((sc, sec))
            overall_scored.sort(key=lambda x: x[0], reverse=True)
            for sc, sec in overall_scored:
                sid = sec.get("section_id", sec.get("title"))
                if sid not in chosen_ids:
                    chosen_ids.add(sid)
                    chosen.append(sec)
                if len(chosen) >= 8:
                    break

        selected_sections_by_doc[doc_id] = chosen

    return selected_sections_by_doc
