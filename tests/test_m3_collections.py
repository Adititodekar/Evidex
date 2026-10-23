"""
Milestone 3 Acceptance Test: Multi-collection isolation and coexistence.
Acceptance criteria:
1. Two collections can coexist simultaneously without interference.
2. Deleting one collection leaves the other collection completely intact and queryable.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ingest.index_build import (
    build_collection_index,
    collection_exists,
    delete_collection,
    CollectionIndex
)

def test_collection_isolation():
    col_a = "test_col_alpha"
    col_b = "test_col_beta"
    
    # Clean up prior test runs if any
    delete_collection(col_a)
    delete_collection(col_b)

    # 1. Build Collection Alpha
    docs_a = [{"doc_id": "report_2025.pdf", "total_pages": 10, "entity": "Alpha Corp", "period": "FY2025", "doc_type": "annual_report"}]
    sections_a = {"report_2025.pdf": [{"section_id": "sec_1", "title": "Financial Highlights", "level": 1, "start_page": 1, "end_page": 5, "summary": "Financials", "keywords": ["ebit", "revenue"]}]}
    chunks_a = [{
        "chunk_id": "report_2025.pdf_p1_c1",
        "doc_id": "report_2025.pdf",
        "page": 1,
        "section": "Financial Highlights",
        "chunk_type": "text",
        "text": "Alpha Corp reports net revenue of 500 million dollars with EBIT growth of 18%.",
        "word_count": 14
    }]
    build_collection_index(col_a, docs_a, sections_a, chunks_a)

    # 2. Build Collection Beta
    docs_b = [{"doc_id": "basel_credit.pdf", "total_pages": 40, "entity": "BCBS", "period": "2024", "doc_type": "regulation"}]
    sections_b = {"basel_credit.pdf": [{"section_id": "sec_1", "title": "Credit Valuation Adjustment", "level": 1, "start_page": 1, "end_page": 20, "summary": "CVA rules", "keywords": ["cva", "derivatives"]}]}
    chunks_b = [{
        "chunk_id": "basel_credit.pdf_p5_c1",
        "doc_id": "basel_credit.pdf",
        "page": 5,
        "section": "Credit Valuation Adjustment",
        "chunk_type": "text",
        "text": "Banks must calculate the credit valuation adjustment for all OTC derivative exposures.",
        "word_count": 12
    }]
    build_collection_index(col_b, docs_b, sections_b, chunks_b)

    # 3. Assert coexistence
    assert collection_exists(col_a), "Collection Alpha does not exist!"
    assert collection_exists(col_b), "Collection Beta does not exist!"
    print("Both collections created and coexisting successfully.", flush=True)

    idx_a = CollectionIndex(col_a)
    idx_b = CollectionIndex(col_b)

    cards_a = idx_a.get_document_cards()
    cards_b = idx_b.get_document_cards()
    assert len(cards_a) == 1 and cards_a[0]["doc_id"] == "report_2025.pdf"
    assert len(cards_b) == 1 and cards_b[0]["doc_id"] == "basel_credit.pdf"

    # Search in Alpha
    hits_a = idx_a.search_vectors("revenue growth", top_k=2)
    assert len(hits_a) > 0 and hits_a[0][0] == "report_2025.pdf_p1_c1"

    # Search in Beta
    hits_b = idx_b.search_vectors("derivative exposure", top_k=2)
    assert len(hits_b) > 0 and hits_b[0][0] == "basel_credit.pdf_p5_c1"

    # 4. Delete Collection Alpha
    delete_collection(col_a)
    assert not collection_exists(col_a), "Collection Alpha was not deleted!"
    print(f"Collection '{col_a}' deleted successfully.", flush=True)

    # 5. Assert Collection Beta remains completely intact
    assert collection_exists(col_b), "Collection Beta was affected by deleting Alpha!"
    idx_b_reloaded = CollectionIndex(col_b)
    reloaded_cards_b = idx_b_reloaded.get_document_cards()
    assert len(reloaded_cards_b) == 1 and reloaded_cards_b[0]["doc_id"] == "basel_credit.pdf"
    
    reloaded_hits_b = idx_b_reloaded.search_vectors("derivative exposure", top_k=2)
    assert len(reloaded_hits_b) > 0 and reloaded_hits_b[0][0] == "basel_credit.pdf_p5_c1"
    print("Collection Beta verified intact and fully queryable after Alpha deletion.", flush=True)

    # Clean up Beta
    delete_collection(col_b)
    print("M3 Acceptance Test PASSED successfully!", flush=True)

if __name__ == "__main__":
    test_collection_isolation()
