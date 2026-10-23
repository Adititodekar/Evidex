"""
OCR fallback module for scanned PDF pages.
Uses rapidocr_onnxruntime if available, with graceful fallback.
"""

import logging
from typing import Optional
import pymupdf as fitz

logger = logging.getLogger(__name__)

_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR initialized successfully.")
        except Exception as e:
            logger.warning(f"RapidOCR initialization failed: {e}. OCR fallback will be unavailable.")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None

def ocr_page(page: fitz.Page, dpi: int = 150, doc_name: Optional[str] = None) -> str:
    """
    Renders a PyMuPDF page as a pixmap and extracts text via OCR.
    Caches results to disk under data/ocr_cache/ to ensure sub-millisecond retrieval on re-runs.
    """
    import os
    from app.config import settings
    
    pno = page.number + 1
    doc_id = doc_name or (os.path.basename(page.parent.name) if hasattr(page, "parent") and page.parent else "doc")
    cache_dir = os.path.join(settings.DATA_DIR, "ocr_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{doc_id}_p{pno}.txt")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    engine = get_ocr_engine()
    if not engine:
        return ""
    try:
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        result, _ = engine(img_bytes)
        if not result:
            return ""
        lines = [line[1].strip() for line in result if line and len(line) > 1 and line[1].strip()]
        text = "\n".join(lines)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text
    except Exception as e:
        logger.error(f"Error performing OCR on page: {e}")
        return ""
