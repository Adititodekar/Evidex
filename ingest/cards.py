"""
Dynamic Metadata Layer: Document Cards and Section Cards generator.
Generates structured metadata per document to eliminate near-duplicate ambiguity.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import pymupdf as fitz

from app.llm import default_llm_client
from ingest.pdf_extract import extract_single_page, normalize_text
from ingest.structure import build_structure_tree

logger = logging.getLogger(__name__)

DOC_CARD_SYSTEM_PROMPT = """You are a senior financial analyst and document classifier.
Your task is to analyze document excerpts (first pages, TOC, and headers) and output strict, precise JSON metadata.
You must be exact about the entity/company name, reporting period (fiscal year or publication date), document type, and jurisdiction.
Never invent information not supported by the excerpt.

Output strict JSON with these keys:
{
  "doc_id": "filename",
  "entity": "Exact legal entity or institution name",
  "doc_type": "annual_report | regulation | proposal | final_rule | guidance | handbook | memo | research_paper",
  "jurisdiction": "Country or Global / International",
  "period": "Exact fiscal year (e.g. FY2025, FY2026) or publication date",
  "status": "final | proposal | draft | annual_report | guidance | research",
  "scope_summary": "3 concise sentences describing scope, core topics, and legal/financial boundaries",
  "key_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "distinguishing_features": "Specific features that distinguish this document from adjacent years, drafts, or related memos"
}"""

SECTION_CARDS_SYSTEM_PROMPT = """You are an expert structure analyzer. Given section titles and page ranges for a document, 
produce a concise 1-2 sentence summary and 3-5 keywords for each section.
Output strict JSON format:
{
  "sections": [
    {
      "section_id": "sec_1",
      "summary": "1-2 sentence summary of content",
      "keywords": ["kw1", "kw2", "kw3"]
    }
  ]
}"""

def build_document_card(doc_path: str, collection_name: str = "default", force_refresh: bool = False) -> Dict[str, Any]:
    """
    Builds or loads a cached Document Card for a given PDF file.
    """
    doc_id = os.path.basename(doc_path)
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", collection_name, "cards")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{doc_id}.card.json")

    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                card = json.load(f)
                if card.get("entity") and card.get("period"):
                    return card
        except Exception as e:
            logger.debug(f"Failed reading cache for {doc_id}: {e}")

    # Extract sample text: pages 1 to 5, plus last page
    doc = fitz.open(doc_path)
    total_pages = len(doc)
    
    sample_pages = list(range(1, min(6, total_pages + 1)))
    if total_pages > 6:
        sample_pages.append(total_pages)

    excerpt_blocks = []
    for pno in sample_pages:
        p_dict = extract_single_page(doc, pno)
        p_text = p_dict["text"][:1200]  # First 1200 chars per page
        excerpt_blocks.append(f"--- Page {pno} of {total_pages} ---\n{p_text}")

    toc_entries = doc.get_toc()[:15]
    doc.close()

    toc_str = "\n".join([f"Level {item[0]}: {item[1]} (p.{item[2]})" for item in toc_entries]) if toc_entries else "None"
    
    user_prompt = f"""Document filename: {doc_id}
Total pages: {total_pages}

Table of Contents / Bookmarks:
{toc_str}

Sample Excerpts:
{chr(10).join(excerpt_blocks)}

Extract the Document Card metadata in strict JSON."""

    try:
        card, usage = default_llm_client.call_structured(
            system_prompt=DOC_CARD_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0
        )
        card["doc_id"] = doc_id
        card["total_pages"] = total_pages
        card["usage"] = usage
        import time
        time.sleep(2.5)
    except Exception as e:
        logger.error(f"Error generating document card for {doc_id}: {e}")
        # Deterministic heuristic fallback
        m_fy = re.search(r'\b(?:FY\s*|Fiscal\s*Year\s*)?(20\d{2})\b', doc_id, re.IGNORECASE)
        detected_period = f"FY{m_fy.group(1)}" if m_fy else "Unknown"
        clean_ent = doc_id.replace(".pdf", "").replace("_", " ")
        clean_ent = re.sub(r'\b(?:FY\s*)?(?:19|20)\d{2}\b', '', clean_ent, flags=re.IGNORECASE)
        clean_ent = re.sub(r'\b(?:annual\s*report|integrated|report)\b', '', clean_ent, flags=re.IGNORECASE).strip()
        card = {
            "doc_id": doc_id,
            "entity": clean_ent or doc_id.replace(".pdf", ""),
            "doc_type": "annual_report" if "annual" in doc_id.lower() or "ar" in doc_id.lower() else "regulation",
            "jurisdiction": "India" if "india" in doc_id.lower() or "ceat" in doc_id.lower() else "US",
            "period": detected_period,
            "status": "final",
            "scope_summary": f"Document covering {clean_ent} for period {detected_period}.",
            "key_topics": ["finance", "reporting", "governance"],
            "distinguishing_features": f"Filing for {doc_id} ({detected_period})",
            "total_pages": total_pages
        }

    # Save to cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write cache file {cache_file}: {e}")

    return card

def build_section_cards(doc_path: str, sections: List[Dict[str, Any]], collection_name: str = "default") -> List[Dict[str, Any]]:
    """
    Builds compact section cards with summaries and keywords for router navigation.
    """
    doc_id = os.path.basename(doc_path)
    if not sections:
        return []

    # Batch sections for summary generation
    sec_summaries = []
    for s in sections:
        # Create a compact card
        sec_summaries.append({
            "section_id": s["section_id"],
            "title": s["title"],
            "level": s["level"],
            "start_page": s["start_page"],
            "end_page": s["end_page"],
            "page_count": s["end_page"] - s["start_page"] + 1,
            "summary": f"Covers {s['title']} spanning pages {s['start_page']} to {s['end_page']}.",
            "keywords": [w.lower() for w in s["title"].split() if len(w) > 3][:5]
        })
    return sec_summaries
