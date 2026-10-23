"""
Near-duplicate sibling detection and discrimination engine.
Solves Failure Mode 1: Distinguishes near-identical documents across reporting years,
draft vs final rules, and memos vs standards.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def normalize_entity_name(name: str) -> str:
    """Normalizes company/institution names for fuzzy clustering."""
    if not name:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', name).lower()
    # Remove fiscal years (e.g. fy2025, fy 2026, 2025, 2026)
    clean = re.sub(r'\b(?:fy\s*)?(?:19|20)\d{2}\b', '', clean)
    clean = re.sub(r'\b(?:fy\s*)?\d{2}\b', '', clean)
    # Remove common suffixes
    for suffix in ["limited", "ltd", "corporation", "corp", "inc", "pjsc", "plc", "llc", "annual report", "annual", "report", "integrated"]:
        clean = re.sub(rf'\b{suffix}\b', '', clean)
    return " ".join(clean.split())

def detect_siblings(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes document cards and identifies sibling pairs/clusters.
    Determines discriminating fields (period, status, jurisdiction, doc_type).
    """
    sibling_table = {}
    
    # Group by normalized entity
    entity_groups: Dict[str, List[Dict[str, Any]]] = {}
    for card in cards:
        norm_entity = normalize_entity_name(card.get("entity", ""))
        # Also group Federal Register or regulatory rules by subject
        doc_id = card.get("doc_id", "")
        if "91fr" in doc_id.lower() or "basel" in doc_id.lower():
            norm_entity = "basel_regulatory_framework"
        elif "fdic" in doc_id.lower() or "cecl" in doc_id.lower():
            norm_entity = "cecl_accounting_guidance"

        if norm_entity not in entity_groups:
            entity_groups[norm_entity] = []
        entity_groups[norm_entity].append(card)

    for norm_entity, group in entity_groups.items():
        if len(group) < 2:
            continue

        for i, card_a in enumerate(group):
            doc_a = card_a["doc_id"]
            siblings_list = []
            values_map = {}
            discriminator = "period"

            for j, card_b in enumerate(group):
                if i == j:
                    continue
                doc_b = card_b["doc_id"]
                siblings_list.append(doc_b)

                # Determine primary discriminator
                period_a = card_a.get("period", "").strip()
                period_b = card_b.get("period", "").strip()
                status_a = card_a.get("status", "").strip()
                status_b = card_b.get("status", "").strip()
                type_a = card_a.get("doc_type", "").strip()
                type_b = card_b.get("doc_type", "").strip()

                if period_a and period_b and period_a != period_b:
                    discriminator = "period"
                    values_map[doc_a] = period_a
                    values_map[doc_b] = period_b
                elif status_a and status_b and status_a != status_b:
                    discriminator = "status"
                    values_map[doc_a] = status_a
                    values_map[doc_b] = status_b
                elif type_a and type_b and type_a != type_b:
                    discriminator = "doc_type"
                    values_map[doc_a] = type_a
                    values_map[doc_b] = type_b
                else:
                    discriminator = "distinguishing_features"
                    values_map[doc_a] = card_a.get("distinguishing_features", doc_a)
                    values_map[doc_b] = card_b.get("distinguishing_features", doc_b)

            sibling_table[doc_a] = {
                "siblings": siblings_list,
                "discriminator": discriminator,
                "values": values_map,
            }

    return sibling_table

def save_siblings(sibling_table: Dict[str, Any], collection_name: str = "default") -> str:
    """Saves sibling table to disk under collection directory."""
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", collection_name)
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "siblings.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(sibling_table, f, indent=2)
    return out_file
