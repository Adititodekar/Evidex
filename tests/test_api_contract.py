"""
API Contract Acceptance Test (Milestone 6).
Verifies POST /index and POST /query match the exact hackathon schema and deliverable contract.
"""

import os
import sys
import io
import zipfile
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api import app
from ingest.index_build import delete_collection

client = TestClient(app)

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"

def test_index_and_query_api_contract():
    test_col = "api_contract_test"
    delete_collection(test_col)

    # 1. Create an in-memory zip archive with a sample PDF from Train
    sample_pdf_path = os.path.join(os.path.dirname(__file__), "..", "Train", "Documents", "2f_lmf.pdf")
    assert os.path.exists(sample_pdf_path), "Sample PDF 2f_lmf.pdf must exist"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(sample_pdf_path, arcname="2f_lmf.pdf")
    zip_buffer.seek(0)

    # 2. Test POST /index
    files = {"file": ("test_docs.zip", zip_buffer, "application/zip")}
    data = {"collection_name": test_col}

    resp = client.post("/index", files=files, data=data)
    assert resp.status_code == 200, f"Index failed: {resp.text}"
    idx_res = resp.json()

    assert idx_res["status"] == "success"
    assert idx_res["collection_name"] == test_col
    assert idx_res["documents_indexed"] == 1
    assert idx_res["chunks_created"] > 0
    assert "indexing_time_s" in idx_res

    # 3. Test POST /query
    query_payload = {
        "collection_name": test_col,
        "query": "What is the primary formulation of the local volatility model described?"
    }

    resp = client.post("/query", json=query_payload)
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    q_res = resp.json()

    # Verify top-level contract keys
    assert "answer" in q_res
    assert isinstance(q_res["answer"], str)
    assert len(q_res["answer"]) > 0

    assert "chunks" in q_res
    assert isinstance(q_res["chunks"], list)
    assert len(q_res["chunks"]) > 0
    first_chunk = q_res["chunks"][0]
    for key in ["chunk_id", "document", "page", "section", "text"]:
        assert key in first_chunk, f"Chunk missing key {key}"

    assert "trace" in q_res
    assert isinstance(q_res["trace"], list)
    assert len(q_res["trace"]) >= 7
    for step in q_res["trace"]:
        for key in ["step_name", "description", "input", "output"]:
            assert key in step, f"Trace step missing key {key}"

    assert "usage" in q_res
    for key in ["total_input_tokens", "total_output_tokens", "total_cost_usd", "latency_s"]:
        assert key in q_res["usage"], f"Usage missing key {key}"

    # Clean up test collection
    delete_collection(test_col)
    print("\nAPI Contract Test PASSED successfully!")

if __name__ == "__main__":
    test_health_check()
    test_index_and_query_api_contract()
