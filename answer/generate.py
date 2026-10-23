"""
Grounded Answer Generation Engine.
Synthesizes verified context into institutional-grade financial answers
with strict [Doc p.X] inline citations, executive summaries, tables, and abstention handling.
"""

import os
import re
import logging
from typing import Dict, Any, Tuple, Optional

from app.config import settings
from app.llm import default_llm_client

logger = logging.getLogger(__name__)

ANSWER_SYSTEM_PROMPT = """You are an elite financial research copilot providing rigorous, factual synthesis for institutional investment committees, regulators, and risk executives.
Your answers must be completely and strictly grounded in the provided document excerpts.

CRITICAL INSTRUCTIONS:
1. Executive Summary: Begin with a "## Bottom line" or "**Short answer:**" section that directly and concisely answers the user's question with key findings and exact metrics.
2. Section Headings: Organize the analysis under logical markdown headings (e.g. `## Section Title` or `### Subsection`).
3. Strict Citations: Every single factual assertion, number, percentage, date, accounting entry, or policy statement MUST be immediately cited using exact brackets: `[Document_Name.pdf p.X]`.
4. Comparison Tables: When comparing multiple fiscal years, entities, or regulatory provisions, present them in clean markdown tables with explicit column headers and units.
5. Absolute Fidelity & Zero Hallucination: Use only facts explicitly stated in the context excerpts. Never speculate, extrapolate, or bring in outside training data.
6. Abstention on Missing Evidence: If the provided excerpts do not contain the information required to answer the question, or if the document does not report the requested metric, return exactly:
"No information was retrieved for this question."
Do not attempt to guess or partially answer if the core metric is absent."""

def format_user_prompt(query: str, context_str: str, q_info: Optional[Dict[str, Any]] = None) -> str:
    facets_text = ""
    if q_info and q_info.get("facets"):
        f_list = [f"- {f.get('description', '')}" for f in q_info["facets"]]
        facets_text = "Key Facets to address:\n" + "\n".join(f_list) + "\n\n"

    return f"""User Query:
{query}

{facets_text}Provided Document Excerpts:
{context_str}

Please generate the comprehensive, strictly grounded answer following the required formatting and citation standards."""

def generate_answer(
    query: str,
    context_str: str,
    q_info: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates a grounded financial research answer from retrieved context.
    Returns (answer_text, usage_metrics).
    """
    # 1. Quick abstention check: if no context retrieved
    if not context_str or not context_str.strip() or "No relevant evidence" in context_str:
        return "No information was retrieved for this question.", {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "latency_s": 0.0,
            "model": "rule_based_abstention"
        }

    user_prompt = format_user_prompt(query, context_str, q_info)
    target_model = model or settings.ANSWER_MODEL

    try:
        answer_text, usage = default_llm_client.call_text(
            system_prompt=ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=target_model,
            max_tokens=4096,
            temperature=0.0
        )
        return answer_text, usage
    except Exception as e:
        logger.error(f"Error calling LLM for answer generation: {e}")
        # Deterministic fallback answer from context
        fallback_answer = f"Based on the retrieved documents:\n\n{context_str[:2000]}"
        return fallback_answer, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "latency_s": 0.0,
            "model": "fallback_extract"
        }
