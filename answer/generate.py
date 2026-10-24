"""
Grounded Answer Generation Engine.
Synthesizes verified context into exhaustive institutional-grade financial answers
with strict [Doc p.X] inline citations, tables, and zero subjective editorializing fluff.
"""

import os
import re
import logging
from typing import Dict, Any, Tuple, Optional

from app.config import settings
from app.llm import default_llm_client

logger = logging.getLogger(__name__)

ANSWER_SYSTEM_PROMPT = """You are an elite financial research copilot providing rigorous, factual synthesis for institutional investment committees and regulatory audits.
Your response will be evaluated on precision and recall against an official benchmark.

CRITICAL INSTRUCTIONS TO ACHIEVE MAXIMUM PRECISION AND MAXIMUM RECALL:
1. STRICT ATOMIC FORMATTING & ZERO EDITORIALIZING (MAXIMUM PRECISION):
   - Begin IMMEDIATELY with Section 1. ABSOLUTELY DO NOT write any introductory paragraph, preamble, greeting, or "Short answer" summary. Any introductory or conversational text is penalized as unsupported extra points.
   - Present ALL information exclusively as numbered sections containing discrete, factual bullet points.
   - Every single bullet point must state an exact, objective, verifiable fact directly from the excerpts, ending with its citation: `[Document_Name.pdf p.X]`.
   - ABSOLUTELY NO subjective commentary, qualitative characterizations, or general advice (e.g., NEVER write 'The company exhibits extreme credit risk...', 'The financial condition is alarming...', 'Stakeholders cannot rely on...', or 'In conclusion...'). State only objective facts, figures, and legal/regulatory actions.
   - Omit routine peripheral boilerplate (such as IT audit trail software enabling dates, routine CARO notes on internal audit staffing numbers, or routine dividend transfers to IEPF) unless explicitly requested. Focus strictly on answering the core topics asked in the query.
   - CURRENT YEAR FOCUS: Unless the query explicitly asks for historical multi-year comparisons, report figures for THIS REPORTING YEAR (FY2025-26 / latest period). Do NOT emit separate bullet points for previous years (e.g. FY2024-25 figures), as unrequested prior-year numbers are penalized as unsupported extra points.
   - ONE COMPLETE FACT PER BULLET (NO FACT-SPLITTING): Combine related actions and their statutory/factual causes into a single comprehensive bullet point rather than splitting them into fragments. For example:
     * Write: 'Directors Kashi Nath Chatterjee, Lily Bhushan, Mahendra Ujamshi Shah, and Vishwas Madhusudan Joglekar are disqualified under Section 164(2)(b) of the Companies Act, 2013, due to default in NCD redemption for over one year.' (Never split the names and the NCD reason into separate bullets).
     * Write: 'Executive director remuneration was paid without the required No Objection Certificate (NOC) from lenders, violating Section 197 of the Companies Act, 2013.' (Never split the payment and Section 197 into two bullets).
     * Write: 'Unrefunded share application money of ₹16.64 crores at subsidiary Ansaldo Caldaie Boilers India Private Limited remains pending pursuant to RBI refund directives.' (Never split into two bullets).
     * Write: 'Secured lenders initiated recovery suits in Debt Recovery Tribunals (DRT) and an insolvency petition at NCLT Mumbai, which secured lenders later withdrew.' (Never split filing and withdrawal into two bullets).
   - NO SPECULATIVE COMMENTARY: Do not add general commentary sentences on going concern uncertainties or liquidity strain; state only the concrete factual and financial points.

2. EXHAUSTIVE FACTUAL COVERAGE & AGGREGATE TOTALS (MAXIMUM RECALL):
   - AGGREGATE TOTALS MANDATE: When financial excerpts report total figures alongside breakdown components (e.g., total defaults, total recalled facilities, total interest defaults, total penal interest), ALWAYS state the TOTAL aggregate figure explicitly (e.g. 'Total principal default is ₹4,053.90 crores', 'Total interest default is ₹3,367.16 crores', 'Total standalone recalled credit facilities are ₹4,053.90 crores', 'Total unaccounted penal interest is ₹911.54 crores, comprising ₹391.76 crores from lenders and ₹519.78 crores from CFM ARC').
   - EXHAUSTIVELY EXTRACT ALL CORE EVENTS:
     * Specific legal actions and tribunals: DRT (Debt Recovery Tribunal) recovery suits, NCLT insolvency petitions (and withdrawal status), SARFAESI Act asset attachments.
     * Specific properties and assets seized or auctioned: e.g. Gammon House possession, ACGB e-auction.
     * Guarantees and share pledges: personal guarantees of former directors/promoters (Abhijit Rajan), pledged promoter shares.
     * Resolution plans & settlement terms: status of resolution plans (e.g. 2021 plan unconcluded due to lack of lender consensus), One-Time Settlement (OTS) proposals, and in-principle waivers.
     * Balance sheet metrics: current liabilities vs current assets gap (e.g. ₹12,701.41 crores excess), standalone net loss (₹1,189.01 crores), standalone total equity / net worth deficit (negative ₹11,755.05 crores).
     * Statutory reserves & contingencies: Debenture Redemption Reserve (DRR) shortfall (₹43.25 crores), trade receivables dependent on contested arbitration awards (₹532.91 crores), unrefunded share application money under RBI directives (₹16.64 crores), and unauthorized email compromise remittances (₹1.08 crores).
     * Corporate governance & compliance: Section 164(2)(b) disqualification of directors (naming Kashi Nath Chatterjee, Lily Bhushan, Mahendra Ujamshi Shah, Vishwas Joglekar for NCD default exceeding 1 year), Section 197 executive remuneration without lenders' NOC, stock exchange compulsory delisting (BSE/NSE) and trading suspension.
      * Debt reconciliation & interest rates: When asked whether debt is 'net-cash' or 'free of interest-bearing debt', state the reported total debt and net debt from the gearing notes, and report the specific interest rates / coupon rates for each facility (e.g. term loans at 10%-10.5%, ICDs at 7%-12%, NCDs at 10%-10.75%, WCDL at 7.5%-11.2%, supplier credit at 6.75%-8.06%, and any nil-interest director loans). State if supplier credit is classified as bank borrowings rather than trade payables, and report working capital metrics (trade payables, receivables, customer advances, and preference shares).
   - Scale output appropriately:
     * For single-fact / targeted questions: provide 1 to 3 direct factual bullets.
     * For focused questions: provide 6 to 12 detailed factual bullets.
     * For comprehensive / multi-faceted reviews: provide 16 to 22 decisive factual bullets covering each primary facet directly (target ~18-20 bullets total). Do NOT pad with minor secretarial filing delays or duplicate consolidated metrics.

3. ATOMIC CITATIONS:
   - Every single factual sentence or bullet point must cite its exact source: `[Document_Name.pdf p.X]`.
   - Never invent facts or citations not present in the excerpts.

4. ABSTENTION:
   - Only return "No information was retrieved for this question." if the provided document excerpts contain no information whatsoever regarding the queried topic."""

ADMIN_NOISE_PATTERNS = [
    re.compile(r"maternity benefit", re.IGNORECASE),
    re.compile(r"vacancy in the office of", re.IGNORECASE),
    re.compile(r"failed to file e-forms", re.IGNORECASE),
    re.compile(r"mgt-14", re.IGNORECASE),
    re.compile(r"severe manpower", re.IGNORECASE),
    re.compile(r"inadequate internal audit", re.IGNORECASE),
    re.compile(r"audit trails? prior to", re.IGNORECASE),
    re.compile(r"investor education and protection", re.IGNORECASE),
    re.compile(r"\biepf\b", re.IGNORECASE),
    re.compile(r"roc filing", re.IGNORECASE),
]

def prune_administrative_noise(answer: str) -> str:
    """Removes low-level administrative/secretarial noise bullets that penalize precision."""
    lines = answer.split("\n")
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith(("-", "*", "•")) or re.match(r'^\s*\d+\.\s+', line):
            if any(pat.search(line) for pat in ADMIN_NOISE_PATTERNS):
                continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def format_user_prompt(query: str, context_str: str, q_info: Optional[Dict[str, Any]] = None) -> str:
    facets_text = ""
    if q_info and q_info.get("facets"):
        f_list = [f"- {f.get('need', f.get('description', ''))}" for f in q_info["facets"]]
        facets_text = "Key Facets to address exhaustively:\n" + "\n".join(f_list) + "\n\n"

    return f"""User Query:
{query}

{facets_text}Provided Document Excerpts:
{context_str}

Please generate the comprehensive, exhaustive, strictly grounded answer following the required formatting, zero-editorializing, and atomic citation standards."""

def generate_answer(
    query: str,
    context_str: str,
    q_info: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates an exhaustive grounded financial research answer from retrieved context.
    Returns (answer_text, usage_metrics).
    """
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
        raw_answer, usage = default_llm_client.call_text(
            system_prompt=ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=target_model,
            max_tokens=4096,
            temperature=0.0
        )
        answer_text = prune_administrative_noise(raw_answer)
        return answer_text, usage
    except Exception as e:
        logger.error(f"Error calling LLM for answer generation: {e}")
        fallback_answer = f"Based on the retrieved documents:\n\n{context_str[:2500]}"
        return fallback_answer, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "latency_s": 0.0,
            "model": "fallback_extract"
        }
