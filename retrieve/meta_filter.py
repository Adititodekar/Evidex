"""
Step 2: Metadata Filtering and Sibling Discrimination.
Solves Failure Mode 1: Eliminates near-duplicate cross-contamination using structured metadata cards.
"""

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

from retrieve.understand import extract_doc_keywords

def filter_documents_by_metadata(
    understanding: Dict[str, Any],
    doc_cards: List[Dict[str, Any]],
    sibling_table: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Filters document cards based on extracted entities, resolved periods, and sibling discriminators.
    Returns: (selected_doc_ids, trace_logs)
    """
    logs = []
    query_entities = [e.lower() for e in understanding.get("entities", [])]
    query_periods = [p.lower() for p in understanding.get("periods", [])]
    is_comparison = understanding.get("is_comparison", False)

    candidates = []

    # 1. Match by Entity
    if query_entities:
        for card in doc_cards:
            doc_id = card["doc_id"]
            ent = card.get("entity", "").lower()
            norm_id = doc_id.lower().replace("_", " ")
            doc_kws = [k.lower() for k in extract_doc_keywords(doc_id, ent)]
            
            matched = False
            for qe in query_entities:
                clean_qe = qe.strip().lower()
                if not clean_qe:
                    continue
                if clean_qe in ent or clean_qe in norm_id or ent in clean_qe:
                    matched = True
                    break
                if any(kw in clean_qe for kw in doc_kws if len(kw) >= 3):
                    matched = True
                    break
                if any(clean_qe in kw for kw in doc_kws if len(clean_qe) >= 3):
                    matched = True
                    break
            if matched:
                candidates.append(doc_id)
        logs.append(f"Entity filter matched {len(candidates)} documents for entities {query_entities}.")

    # If no entity matched or entity was not specified, keep all as initial pool
    if not candidates:
        candidates = [card["doc_id"] for card in doc_cards]
        logs.append(f"No specific entity filter applied; evaluating all {len(candidates)} documents.")

    # 2. Sibling Discrimination (Failure Mode 1)
    surviving_docs = []
    visited_siblings = set()

    for doc_id in candidates:
        if doc_id in visited_siblings:
            continue

        sib_info = sibling_table.get(doc_id)
        if not sib_info or not sib_info.get("siblings"):
            surviving_docs.append(doc_id)
            continue

        siblings = sib_info["siblings"]
        all_family = [doc_id] + [s for s in siblings if s in candidates]

        if is_comparison:
            # Query explicitly compares versions/years -> keep all family members
            surviving_docs.extend(all_family)
            visited_siblings.update(all_family)
            logs.append(f"Comparison query: retained sibling cluster {all_family}.")
        else:
            # Single-target query -> discriminate by period or status
            discriminator = sib_info.get("discriminator", "period")
            values = sib_info.get("values", {})
            
            chosen_doc = None
            if discriminator == "period":
                # Check for explicit year in query periods
                for p in query_periods:
                    for d in all_family:
                        d_val = str(values.get(d, "")).lower()
                        if p.replace("fy", "") in d_val or p in d_val:
                            chosen_doc = d
                            break
                    if chosen_doc:
                        break

                # If query asks for 'latest', pick the highest period/year
                if not chosen_doc and ("latest" in query_periods or not query_periods):
                    all_family.sort(key=lambda d: str(values.get(d, "")), reverse=True)
                    chosen_doc = all_family[0]

            if not chosen_doc:
                chosen_doc = all_family[0]

            surviving_docs.append(chosen_doc)
            visited_siblings.update(all_family)
            logs.append(f"Sibling discrimination: picked '{chosen_doc}' over siblings {all_family} via '{discriminator}'.")

    # Fallback guard
    if not surviving_docs:
        surviving_docs = [c["doc_id"] for c in doc_cards[:5]]
        logs.append("Fallback: retained top 5 default documents.")

    return list(set(surviving_docs)), logs
