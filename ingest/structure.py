
"""
Document structure and section hierarchy extraction.
Parses native PDF bookmarks/TOC and falls back to heading detection from text formatting.
"""

import re
import logging
from typing import List, Dict, Any, Optional
import pymupdf as fitz

logger = logging.getLogger(__name__)

# Heuristic heading regex patterns
HEADING_PATTERNS = [
    re.compile(r'^(?:Chapter|Section|Part|ARTICLE|Item|Note)\s+([0-9A-Z]+(?:\.[0-9A-Z]+)*)\b[:\.\s]*(.*)', re.IGNORECASE),
    re.compile(r'^([0-9]+(?:\.[0-9]+)+)\s+(.*)'),  # e.g., 3.2.1 Market Risk
    re.compile(r'^([A-Z\s]{4,60})$'),  # ALL CAPS headings
]

def clean_toc_title(title: str) -> str:
    """Removes hash-like titles or cleans noise from TOC entries."""
    if not title:
        return ""
    # Filter out 64-char hex hashes (e.g. ac6a73b0b6e8096ecf554d28283e700782df6006439c948c2e42adda7f9171d8.pdf)
    if re.match(r'^[0-9a-f]{32,64}(?:\.pdf)?$', title.strip(), re.IGNORECASE):
        return ""
    return title.strip()

def extract_toc_sections(doc: fitz.Document, total_pages: int) -> List[Dict[str, Any]]:
    """
    Extracts sections from PyMuPDF get_toc() and establishes page ranges.
    """
    raw_toc = doc.get_toc()
    if not raw_toc or len(raw_toc) < 2:
        return []

    valid_entries = []
    for item in raw_toc:
        level, title, pno = item[0], clean_toc_title(item[1]), item[2]
        if title and 1 <= pno <= total_pages:
            valid_entries.append({
                "level": level,
                "title": title,
                "start_page": pno,
            })

    if len(valid_entries) < 2:
        return []

    sections = []
    for i, entry in enumerate(valid_entries):
        start = entry["start_page"]
        # Find end page: min of next entry with same or lower level, or document end
        end = total_pages
        for j in range(i + 1, len(valid_entries)):
            if valid_entries[j]["level"] <= entry["level"]:
                end = max(start, valid_entries[j]["start_page"] - 1)
                break
        sections.append({
            "section_id": f"sec_{i+1}",
            "title": entry["title"],
            "level": entry["level"],
            "start_page": start,
            "end_page": end,
        })
    return sections

def detect_headings_from_text(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback heading detector scanning extracted pages for section titles.
    """
    sections = []
    total_pages = len(pages)
    
    for p in pages:
        pno = p["page_number"]
        lines = p["text"].split("\n")
        for line in lines[:8]:  # Top 8 lines of each page
            line_str = line.strip()
            if len(line_str) < 4 or len(line_str) > 100:
                continue
            for pat in HEADING_PATTERNS:
                m = pat.match(line_str)
                if m:
                    sections.append({
                        "section_id": f"sec_{len(sections)+1}",
                        "title": line_str,
                        "level": 1 if not pat.pattern.startswith(r'^([0-9]+(?:\.[0-9]+)+)') else 2,
                        "start_page": pno,
                    })
                    break

    # Deduplicate closely spaced identical headings
    filtered = []
    for s in sections:
        if not filtered or s["title"] != filtered[-1]["title"]:
            filtered.append(s)

    # Compute page boundaries
    final_sections = []
    for i, entry in enumerate(filtered):
        start = entry["start_page"]
        end = total_pages if i + 1 == len(filtered) else max(start, filtered[i + 1]["start_page"] - 1)
        final_sections.append({
            "section_id": entry["section_id"],
            "title": entry["title"],
            "level": entry["level"],
            "start_page": start,
            "end_page": end,
        })
    return final_sections

def build_structure_tree(pdf_path: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Builds the section tree for a document.
    Prioritizes native TOC; falls back to text-based heading detection;
    falls back to fixed page windows (15 pages) if document has no headings.
    """
    total_pages = len(pages)
    doc = fitz.open(pdf_path)
    sections = extract_toc_sections(doc, total_pages)
    doc.close()

    if not sections or len(sections) < 3:
        text_sections = detect_headings_from_text(pages)
        if len(text_sections) >= 3:
            sections = text_sections

    # Default fallback: chunk into 15-page logical sections
    if not sections:
        window_size = 15
        sec_idx = 1
        for start_p in range(1, total_pages + 1, window_size):
            end_p = min(total_pages, start_p + window_size - 1)
            sections.append({
                "section_id": f"sec_{sec_idx}",
                "title": f"Pages {start_p}-{end_p}",
                "level": 1,
                "start_page": start_p,
                "end_page": end_p,
            })
            sec_idx += 1

    return sections

def find_section_path_for_page(sections: List[Dict[str, Any]], page_num: int) -> str:
    """
    Returns the title of the most specific section containing the given page number.
    """
    matching = [s for s in sections if s["start_page"] <= page_num <= s["end_page"]]
    if not matching:
        return f"Page {page_num}"
    # Sort by highest level (deepest) then narrowest page range
    matching.sort(key=lambda s: (-s["level"], s["end_page"] - s["start_page"]))
    return matching[0]["title"]
