"""
Step 1: Query Understanding and Facet Decomposition.
Deconstructs complex analyst questions into actionable facets, entities, periods, and evidence breadth.
"""

import re
import json
import logging
from typing import Dict, Any, List

from app.llm import LLMClient

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

COMMON_DOMAIN_WORDS = {
    "board", "bank", "banks", "market", "risk", "credit", "financial", "reserve", "system",
    "currency", "group", "statement", "fact", "sheet", "summary", "memo", "approach",
    "standardized", "framework", "paper", "comparison", "update", "model", "handbook",
    "implementation", "research", "academic", "notes", "accounts", "limited", "limit",
    "overview", "audit", "auditors", "director", "directors", "management", "company",
    "governance", "corporate", "capital", "borrowings", "debt", "loans", "letter", "press",
    "release", "report", "annual", "integrated", "industry", "industries", "overseas",
    "coatings", "metal", "wind", "india", "properties", "standard", "standards",
    "insurance", "deposit", "office", "corporation", "governors", "federal", "the", "and", "for", "with"
}

def extract_doc_keywords(doc_id: str, entity: str = "") -> List[str]:
    """Dynamically extracts distinctive keywords and phrases for any document in any collection."""
    terms = set()
    clean_id = re.sub(r'\.pdf$', '', doc_id, flags=re.IGNORECASE).replace('_', ' ').replace('-', ' ')
    clean_id = re.sub(r'\b(annual|report|integrated|fy\s*20\d{2}|fy\s*2526|20\d{2}|2526|re)\b', '', clean_id, flags=re.IGNORECASE).strip()
    clean_id = re.sub(r'\s+', ' ', clean_id)
    
    # 1. Full multi-word clean title
    if len(clean_id) > 2 and ' ' in clean_id:
        terms.add(clean_id.lower())
        
    # 2. Distinctive single words (excluding domain stopwords)
    for part in clean_id.split():
        p_clean = part.lower().strip()
        if len(p_clean) >= 3 and p_clean not in COMMON_DOMAIN_WORDS:
            terms.add(p_clean)

    # 3. Clean entity if known
    if entity and entity not in ("Unknown", "None", "Academic Research"):
        clean_ent = re.sub(r'\b(limited|ltd|pjsc|annual report|integrated annual report|annual|report)\b', '', entity, flags=re.IGNORECASE).strip()
        if len(clean_ent) > 2:
            terms.add(clean_ent.lower())
            for part in clean_ent.split():
                p_clean = part.lower().strip('(),;')
                if len(p_clean) >= 3 and p_clean not in COMMON_DOMAIN_WORDS:
                    terms.add(p_clean)
    return list(terms)

def understand_query(query: str, doc_cards: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Deconstructs query into facets, entities, temporal periods, and scope.
    Combines LLM intelligence with deterministic entity & period extraction as robust fallback.
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

    # Match entities and core document keywords from known corpus doc cards
    if doc_cards:
        for card in doc_cards:
            doc_id = card.get("doc_id", "")
            ent = card.get("entity", "")
            kws = extract_doc_keywords(doc_id, ent)
            for kw in kws:
                if len(kw) >= 3 and re.search(r'\b' + re.escape(kw) + r'\b', clean_q, re.IGNORECASE):
                    # Add canonical entity or clean keyword
                    match_name = ent if (ent and ent not in ("Unknown", "None", "Academic Research")) else kw
                    if match_name not in found_entities:
                        found_entities.append(match_name)
                    break

    is_comparison = bool(re.search(r'\b(compare|versus|vs\.?|difference|between|across|both)\b', clean_q, re.IGNORECASE))
    
    # Determine default breadth
    words_count = len(clean_q.split())
    if words_count > 30 or "all" in clean_q.lower() or "every" in clean_q.lower() or is_comparison:
        breadth = "broad"
    elif words_count > 15:
        breadth = "medium"
    else:
        breadth = "narrow"

    # Facet decomposition (heuristic base)
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

    # 2. LLM-assisted enhancement (if available)
    try:
        client = LLMClient()
        resp, _ = client.call_structured(
            system_prompt=UNDERSTAND_SYSTEM_PROMPT,
            user_prompt=clean_q,
            max_tokens=1024,
            temperature=0.0
        )
        if resp:
            llm_entities = resp.get("entities", [])
            for e in llm_entities:
                if e and e not in found_entities:
                    found_entities.append(e)
            
            llm_periods = resp.get("periods", [])
            for p in llm_periods:
                if p and p not in found_periods:
                    found_periods.append(p)
                    
            if resp.get("is_comparison") is True:
                is_comparison = True
            if resp.get("breadth"):
                breadth = resp.get("breadth")
            if resp.get("facets"):
                facets = resp.get("facets")
    except Exception as e:
        logger.warning(f"LLM query understanding fallback to deterministic: {e}")

    # If multiple entities found, mark as comparison
    if len(found_entities) > 1 and not is_comparison:
        if any(term in clean_q.lower() for term in ["line up", "rank", "list", "and", "between", "across"]):
            is_comparison = True
            breadth = "broad"

    return {
        "facets": facets,
        "entities": found_entities,
        "periods": found_periods,
        "jurisdictions": ["Global", "US", "India"],
        "is_comparison": is_comparison,
        "breadth": breadth,
        "is_unanswerable_expected": "not found" in clean_q.lower()
    }
