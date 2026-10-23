"""
Step 1: Query Understanding and Facet Decomposition.
Deconstructs complex analyst questions into actionable facets, entities, periods, and evidence breadth.
"""

import re
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

UNDERSTAND_SYSTEM_PROMPT = """You are a senior financial analyst assistant.
Analyze the user's research query and deconstruct it into structured search facets.
Output strict JSON with these fields:
{
  "facets": [
    {
      "facet_id": "f1",
      "need": "Specific factual point to retrieve (e.g. 'CECL calculation formula', 'EBITDA for FY26')",
      "aspect": "definition | numerical | comparison | risk_event | disclosure",
      "expected_doc_types": ["annual_report", "guidance"]
    }
  ],
  "entities": ["entity1", "entity2"],
  "periods": ["FY2026", "latest"],
  "jurisdictions": ["India", "United States", "Global"],
  "is_comparison": false,
  "breadth": "narrow | medium | broad",
  "is_unanswerable_expected": false
}"""

def understand_query(query: str, doc_cards: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Deconstructs query into facets, entities, temporal periods, and scope.
    Includes deterministic entity & period extraction as robust heuristic.
    """
    clean_q = query.strip()
    
    # 1. Deterministic heuristic extraction
    found_entities = []
    found_periods = []
    
    # Extract years (FY2025, 2026, etc.)
    years = re.findall(r'\b(?:FY\s*)?(20\d{2})\b', clean_q, re.IGNORECASE)
    for y in years:
        found_periods.append(f"FY{y}")
    if "latest" in clean_q.lower() or "current" in clean_q.lower() or "this year" in clean_q.lower():
        found_periods.append("latest")

    # Match entities from known corpus doc cards if provided
    if doc_cards:
        for card in doc_cards:
            ent = card.get("entity", "")
            if ent and len(ent) > 3 and ent.lower() in clean_q.lower():
                if ent not in found_entities:
                    found_entities.append(ent)

    is_comparison = bool(re.search(r'\b(compare|versus|vs\.?|difference|between)\b', clean_q, re.IGNORECASE))
    
    # Determine breadth
    words_count = len(clean_q.split())
    if words_count > 30 or "all" in clean_q.lower() or "every" in clean_q.lower() or is_comparison:
        breadth = "broad"
    elif words_count > 15:
        breadth = "medium"
    else:
        breadth = "narrow"

    # Facet decomposition
    sentences = [s.strip() for s in re.split(r'[?;.]', clean_q) if len(s.strip()) > 8]
    if not sentences:
        sentences = [clean_q]

    facets = []
    for idx, s in enumerate(sentences[:4]):
        facets.append({
            "facet_id": f"f{idx+1}",
            "need": s,
            "aspect": "comparison" if is_comparison else "numerical",
            "expected_doc_types": ["annual_report", "regulation"]
        })

    return {
        "facets": facets,
        "entities": found_entities,
        "periods": found_periods,
        "jurisdictions": ["Global", "US", "India"],
        "is_comparison": is_comparison,
        "breadth": breadth,
        "is_unanswerable_expected": "not found" in clean_q.lower()
    }
