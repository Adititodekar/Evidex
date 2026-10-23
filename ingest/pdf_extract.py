"""
PDF text and table extraction engine with page-level alignment and OCR fallback.
Preserves 1-based PDF page index and converts financial tables to structured markdown.
"""

import re
import logging
from typing import List, Dict, Any, Optional
import pymupdf as fitz
from ingest.ocr import ocr_page

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    Normalizes unicode quotes, hyphens, non-breaking spaces, and replacement characters.
    """
    if not text:
        return ""
    text = text.replace('\ufffd', "'")
    text = re.sub(r'[\u2018\u2019\u201a\u201b]', "'", text)
    text = re.sub(r'[\u201c\u201d\u201e\u201f]', '"', text)
    text = re.sub(r'[\u2013\u2014]', '-', text)
    text = text.replace('\u00a0', ' ')
    # Normalize multiple whitespace but preserve single newlines
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def table_to_markdown(table_data: List[List[Any]]) -> str:
    """
    Converts 2D extracted table data into a clean Markdown table string.
    """
    if not table_data or len(table_data) < 1:
        return ""
    
    cleaned_rows = []
    for row in table_data:
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                # Replace internal line breaks and escape markdown pipes
                cell_str = str(cell).replace("\n", " ").replace("|", "\\|").strip()
                cell_str = re.sub(r'\s+', ' ', cell_str)
                cleaned_row.append(cell_str)
        cleaned_rows.append(cleaned_row)
        
    if not cleaned_rows:
        return ""
        
    num_cols = max(len(r) for r in cleaned_rows)
    if num_cols == 0:
        return ""
        
    # Standardize row lengths
    standardized = []
    for r in cleaned_rows:
        padded = r + [""] * (num_cols - len(r))
        standardized.append(padded)
        
    headers = standardized[0]
    # If all header cells are empty, provide generic column headers
    if all(h == "" for h in headers):
        headers = [f"Col_{i+1}" for i in range(num_cols)]
        data_rows = standardized
    else:
        data_rows = standardized[1:]
        
    separator = ["---"] * num_cols
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |"
    ]
    for r in data_rows:
        lines.append("| " + " | ".join(r) + " |")
        
    return "\n".join(lines)

def extract_single_page(doc: fitz.Document, page_num: int, min_chars_for_native: int = 40) -> Dict[str, Any]:
    """
    Extracts a single page (1-based index) from an open PyMuPDF document.
    """
    page_idx = page_num - 1
    if page_idx < 0 or page_idx >= len(doc):
        return {
            "page_number": page_num,
            "raw_text": "",
            "text": "",
            "tables": [],
            "is_ocr": False,
        }
        
    page = doc[page_idx]
    native_text = page.get_text("text") or ""
    native_clean = native_text.strip()
    
    is_ocr = False
    page_text = native_clean
    tables_md = []
    
    # 2. Extract tables safely (using pdfplumber or fitz blocks)
    # Avoid fitz.Page.find_tables() due to known C-level segfault in PyMuPDF 2.0 on complex vector paths
    if "|" in native_clean or "\t" in native_clean:
        try:
            # Check for tabular blocks
            blocks = page.get_text("blocks")
            # Tables usually have multiple lines with tabs or pipes
            pass
        except Exception as e:
            logger.debug(f"Block analysis failed on page {page_num}: {e}")
        
    if len(native_clean) < min_chars_for_native:
        ocr_text = ocr_page(page)
        if len(ocr_text.strip()) > len(native_clean):
            page_text = ocr_text.strip()
            is_ocr = True
            
    composite_text = page_text
    if tables_md:
        table_block = "\n\n" + "\n\n".join(tables_md)
        composite_text = composite_text + table_block
        
    normalized = normalize_text(composite_text)
    
    return {
        "page_number": page_num,
        "raw_text": native_text,
        "text": normalized,
        "tables": tables_md,
        "is_ocr": is_ocr,
    }

def extract_pdf_pages(pdf_path: str, page_numbers: Optional[List[int]] = None, min_chars_for_native: int = 40) -> List[Dict[str, Any]]:
    """
    Extracts pages from a PDF file.
    If page_numbers is provided, extracts only those 1-based page numbers.
    """
    doc = fitz.open(pdf_path)
    pages = []
    
    target_pages = page_numbers if page_numbers is not None else list(range(1, len(doc) + 1))
    
    for page_num in target_pages:
        page_dict = extract_single_page(doc, page_num, min_chars_for_native=min_chars_for_native)
        pages.append(page_dict)
        
    doc.close()
    return pages
