"""
Milestone 2 Acceptance Test: Document Cards and Sibling Table Verification.
Acceptance criteria:
1. Document cards exist for all PDFs in Train/Documents with structured metadata.
2. Metal Coatings FY2025 and FY2026 are identified as siblings with 'period' as discriminator.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ingest.cards import build_document_card
from ingest.siblings import detect_siblings, save_siblings

def test_m2_cards_and_siblings():
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "Train", "Documents")
    assert os.path.exists(docs_dir), f"Documents dir missing at {docs_dir}"
    
    pdf_files = [f for f in os.listdir(docs_dir) if f.lower().endswith(".pdf")]
    print(f"Total PDFs in corpus to process: {len(pdf_files)}", flush=True)
    assert len(pdf_files) >= 30, f"Expected at least 30 PDFs, found {len(pdf_files)}"

    cards = []
    for idx, fname in enumerate(pdf_files):
        doc_path = os.path.join(docs_dir, fname)
        card = build_document_card(doc_path, collection_name="train")
        cards.append(card)
        if (idx + 1) % 10 == 0 or idx + 1 == len(pdf_files):
            print(f"Processed card {idx+1}/{len(pdf_files)}: {fname} -> {card.get('entity')} ({card.get('period')})", flush=True)

    assert len(cards) == len(pdf_files), "Mismatch in cards count vs PDF files count!"

    # 1. Verify all cards have core fields
    for card in cards:
        assert card.get("doc_id"), f"Card missing doc_id: {card}"
        assert card.get("entity"), f"Card {card['doc_id']} missing entity!"
        assert card.get("period"), f"Card {card['doc_id']} missing period!"
        assert card.get("doc_type"), f"Card {card['doc_id']} missing doc_type!"

    print("All document cards verified with mandatory metadata fields.", flush=True)

    # 2. Build Sibling Table
    sibling_table = detect_siblings(cards)
    save_path = save_siblings(sibling_table, collection_name="train")
    print(f"Saved sibling table to: {save_path}", flush=True)

    # 3. Acceptance Spot Check: Metal Coatings FY2025 vs FY2026
    doc_fy25 = "Metal Coatings_Annual Report FY 2025.pdf"
    doc_fy26 = "Metal Coatings_Annual Report FY 2026.pdf"

    assert doc_fy25 in sibling_table, f"{doc_fy25} not found in sibling table!"
    assert doc_fy26 in sibling_table, f"{doc_fy26} not found in sibling table!"

    info_fy25 = sibling_table[doc_fy25]
    print(f"Metal Coatings FY25 Sibling Info: {json.dumps(info_fy25, indent=2)}", flush=True)

    assert doc_fy26 in info_fy25["siblings"], f"{doc_fy26} not listed as sibling of {doc_fy25}!"
    assert info_fy25["discriminator"] == "period", f"Expected discriminator 'period', got {info_fy25['discriminator']}"
    
    val_25 = str(info_fy25["values"].get(doc_fy25, ""))
    val_26 = str(info_fy25["values"].get(doc_fy26, ""))
    assert "2025" in val_25 or "25" in val_25, f"Expected 2025 in value: {val_25}"
    assert "2026" in val_26 or "26" in val_26, f"Expected 2026 in value: {val_26}"

    print("M2 Acceptance Test PASSED successfully!", flush=True)

if __name__ == "__main__":
    test_m2_cards_and_siblings()
