"""
Pydantic Schemas for EVIDEX API Endpoints (POST /index and POST /query).
Strictly adheres to the hackathon deliverable contract.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class IndexResponse(BaseModel):
    status: str = Field(..., description="'success' or 'error'")
    collection_name: str
    documents_indexed: int
    chunks_created: int
    indexing_time_s: float
    message: Optional[str] = None

class QueryRequest(BaseModel):
    collection_name: str = Field(..., description="The name of the indexed collection to query")
    query: str = Field(..., description="The analyst or regulatory query")

class RetrievedChunk(BaseModel):
    chunk_id: str
    document: str
    page: int
    section: Optional[str] = ""
    chunk_type: Optional[str] = "text"
    text: str
    word_count: Optional[int] = 0

class TraceStep(BaseModel):
    step_name: str = Field(..., description="Standard step name, e.g. query_understanding, metadata_filter, etc.")
    description: str = Field(..., description="Human-readable description of what this step performed")
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)

class UsageMetrics(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    latency_s: float = 0.0

class QueryResponse(BaseModel):
    answer: str = Field(..., description="The synthesized, grounded financial answer")
    chunks: List[RetrievedChunk] = Field(default_factory=list, description="Verified evidence chunks")
    trace: List[TraceStep] = Field(default_factory=list, description="Exact step-by-step trace array")
    usage: UsageMetrics = Field(default_factory=UsageMetrics, description="Aggregated token usage and cost metrics")
