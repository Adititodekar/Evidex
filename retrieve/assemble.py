"""
Step 7: Context Assembly and Pipeline Orchestrator.
Orders chunks by document and page, formats exact [Doc p.X] citations, and constructs full execution trace.
"""

import time
import logging
from typing import Dict, Any, List, Tuple

from retrieve.understand import understand_query
from retrieve.meta_filter import filter_documents_by_metadata
from retrieve.router import route_sections_for_facets
from retrieve.drilldown import drilldown_evidence_set
from retrieve.coverage import check_and_widen_coverage
from retrieve.verify import verify_and_rank_evidence

logger = logging.getLogger(__name__)

def execute_retrieval_pipeline(
    query: str,
    collection_index: Any,
    sibling_table: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Executes Steps 1 to 6 of the Routed Evidence-Set Retrieval pipeline.
    Returns: (verified_chunks, trace_array, formatted_context_str)
    """
    trace = []
    t_start = time.time()

    # Step 1: Query Understanding
    doc_cards = collection_index.get_document_cards()
    understanding = understand_query(query, doc_cards=doc_cards)
    trace.append({
        "step_name": "query_understanding",
        "description": "Decomposed question into facets, extracted entities, and resolved temporal scope",
        "input": {"query": query},
        "output": {
            "facets_count": len(understanding.get("facets", [])),
            "entities": understanding.get("entities", []),
            "periods": understanding.get("periods", []),
            "breadth": understanding.get("breadth", "medium"),
            "is_comparison": understanding.get("is_comparison", False)
        }
    })

    # Step 2: Metadata Filtering & Sibling Discrimination
    surviving_docs, filter_logs = filter_documents_by_metadata(understanding, doc_cards, sibling_table)
    trace.append({
        "step_name": "metadata_filter",
        "description": "Filtered documents by entity and period, resolving near-duplicate siblings",
        "input": {"entities": understanding.get("entities", []), "periods": understanding.get("periods", [])},
        "output": {"surviving_documents": surviving_docs, "logs": filter_logs}
    })

    # Step 3: Section Routing
    selected_sections = route_sections_for_facets(understanding.get("facets", []), surviving_docs, collection_index)
    total_sections_count = sum(len(secs) for secs in selected_sections.values())
    trace.append({
        "step_name": "doc_router",
        "description": "Navigated section cards per facet to shortlist high-relevance sections",
        "input": {"surviving_documents": len(surviving_docs)},
        "output": {"selected_sections_count": total_sections_count, "documents_routed": list(selected_sections.keys())}
    })

    # Step 4: Recursive Drilldown (Whole-Section Retrieval)
    candidate_chunks = drilldown_evidence_set(
        selected_sections,
        query,
        surviving_docs,
        collection_index,
        breadth=understanding.get("breadth", "medium"),
        facets=understanding.get("facets", [])
    )
    trace.append({
        "step_name": "recursive_drilldown",
        "description": "Retrieved complete leaf sections and targeted multi-vector/BM25 candidates",
        "input": {"sections_count": total_sections_count},
        "output": {"candidate_chunks_count": len(candidate_chunks)}
    })

    # Step 5: Coverage Check & Widening
    widened_chunks, cov_logs = check_and_widen_coverage(
        candidate_chunks,
        surviving_docs,
        collection_index,
        breadth=understanding.get("breadth", "medium")
    )
    trace.append({
        "step_name": "coverage_check",
        "description": "Verified evidence bounds per breadth setting with bounded adaptive widening",
        "input": {"candidates_in": len(candidate_chunks)},
        "output": {"chunks_after_coverage": len(widened_chunks), "logs": cov_logs}
    })

    # Step 6: Evidence Verification
    verified_chunks, ver_logs = verify_and_rank_evidence(
        widened_chunks,
        query,
        breadth=understanding.get("breadth", "medium")
    )
    trace.append({
        "step_name": "evidence_verification",
        "description": "Ranked and verified evidence chunks matching judge relevance criteria",
        "input": {"chunks_in": len(widened_chunks)},
        "output": {"verified_chunks_count": len(verified_chunks), "logs": ver_logs}
    })

    # Step 7: Order chunks by document, then page
    verified_chunks.sort(key=lambda c: (c["document"], c["page"]))

    # Assemble formatted context string with exact citations
    context_lines = []
    for c in verified_chunks:
        doc_name = c["document"]
        pno = c["page"]
        text = c["text"]
        context_lines.append(f"[{doc_name} p.{pno}]\n{text}\n")

    formatted_context = "\n".join(context_lines)
    trace.append({
        "step_name": "context_assembly",
        "description": "Ordered verified chunks by document and page, formatting exact citations",
        "input": {"chunks_count": len(verified_chunks)},
        "output": {
            "formatted_context_length": len(formatted_context),
            "documents_included": sorted(list(set(c["document"] for c in verified_chunks)))
        }
    })
    return verified_chunks, trace, formatted_context
