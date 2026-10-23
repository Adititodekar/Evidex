"""
Paragraph-aware and table-aware document chunker.
Strict invariant: Chunks never cross a page boundary. 
Word budget: ~60 to 250 words per chunk.
"""

import re
import logging
from typing import List, Dict, Any
from ingest.structure import find_section_path_for_page

logger = logging.getLogger(__name__)

def split_long_text_into_sentences(text: str, min_words: int = 50, max_words: int = 250) -> List[str]:
    """
    Splits long text into sentence-bounded chunks of approximately 60-250 words.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    curr_sentences = []
    curr_word_count = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        words = sent.split()
        sent_word_count = len(words)

        # If adding this sentence exceeds max_words and we already have enough words, emit chunk
        if curr_word_count + sent_word_count > max_words and curr_word_count >= min_words:
            chunks.append(" ".join(curr_sentences))
            curr_sentences = [sent]
            curr_word_count = sent_word_count
        else:
            curr_sentences.append(sent)
            curr_word_count += sent_word_count

    if curr_sentences:
        chunks.append(" ".join(curr_sentences))

    return chunks

def chunk_page(doc_id: str, page_dict: Dict[str, Any], sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chunks a single page into paragraph-bounded and table-bounded chunks.
    Guarantees that no chunk crosses the page.
    """
    page_num = page_dict["page_number"]
    page_text = page_dict["text"]
    tables = page_dict.get("tables", [])
    section_name = find_section_path_for_page(sections, page_num)

    chunks = []
    chunk_idx = 1

    # 1. Process structured tables as dedicated table chunks
    for t_idx, tbl in enumerate(tables):
        tbl_words = len(tbl.split())
        # If table is within reasonable size, emit as a single table chunk
        if tbl_words <= 350:
            chunks.append({
                "chunk_id": f"{doc_id}_p{page_num}_t{t_idx+1}",
                "doc_id": doc_id,
                "document": doc_id,
                "page": page_num,
                "section": section_name,
                "chunk_type": "table",
                "text": tbl,
                "word_count": tbl_words,
            })
        else:
            # Split large table into sub-tables preserving header
            lines = tbl.split("\n")
            if len(lines) >= 3:
                header = lines[:2]
                body = lines[2:]
                step = 15
                for sub_i in range(0, len(body), step):
                    sub_tbl = "\n".join(header + body[sub_i:sub_i+step])
                    chunks.append({
                        "chunk_id": f"{doc_id}_p{page_num}_t{t_idx+1}_{sub_i//step+1}",
                        "doc_id": doc_id,
                        "document": doc_id,
                        "page": page_num,
                        "section": section_name,
                        "chunk_type": "table",
                        "text": sub_tbl,
                        "word_count": len(sub_tbl.split()),
                    })

    # 2. Extract prose paragraphs (excluding markdown table blocks if already handled)
    # Remove table blocks from page_text for prose chunking
    prose_text = page_text
    for tbl in tables:
        prose_text = prose_text.replace(tbl, "")

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', prose_text) if p.strip()]

    # Merge small consecutive paragraphs or split oversized ones
    buffer = []
    buffer_words = 0

    def emit_buffer():
        nonlocal chunk_idx, buffer, buffer_words
        if not buffer:
            return
        combined_text = "\n\n".join(buffer)
        is_list = combined_text.strip().startswith(("-", "*", "•")) or bool(re.match(r'^\s*\d+[\.\)]', combined_text))
        chunks.append({
            "chunk_id": f"{doc_id}_p{page_num}_c{chunk_idx}",
            "doc_id": doc_id,
            "document": doc_id,
            "page": page_num,
            "section": section_name,
            "chunk_type": "list" if is_list else "text",
            "text": combined_text,
            "word_count": buffer_words,
        })
        chunk_idx += 1
        buffer = []
        buffer_words = 0

    for para in paragraphs:
        words = para.split()
        p_word_count = len(words)
        if p_word_count == 0:
            continue

        if p_word_count > 250:
            # Emit pending buffer first
            emit_buffer()
            # Split long paragraph by sentences
            sub_chunks = split_long_text_into_sentences(para, min_words=50, max_words=200)
            for sub in sub_chunks:
                chunks.append({
                    "chunk_id": f"{doc_id}_p{page_num}_c{chunk_idx}",
                    "doc_id": doc_id,
                    "document": doc_id,
                    "page": page_num,
                    "section": section_name,
                    "chunk_type": "text",
                    "text": sub,
                    "word_count": len(sub.split()),
                })
                chunk_idx += 1
        elif buffer_words + p_word_count <= 250:
            buffer.append(para)
            buffer_words += p_word_count
            if buffer_words >= 60:
                emit_buffer()
        else:
            emit_buffer()
            buffer.append(para)
            buffer_words = p_word_count

    emit_buffer()
    return chunks

def chunk_document(doc_id: str, pages: List[Dict[str, Any]], sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chunks an entire document across all pages.
    Guarantees every chunk has an exact 1-based page number.
    """
    all_chunks = []
    for page_dict in pages:
        chunks = chunk_page(doc_id, page_dict, sections)
        all_chunks.extend(chunks)
    return all_chunks
