"""
Central configuration for EVIDEX: Routed Evidence-Set Retrieval (RERS).
"""

import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENCODE_API_KEY: str = os.getenv("OPENCODE_API_KEY", "")
    
    # Priority endpoint configuration
    # Default to Gemini if GEMINI_API_KEY is present, else OpenCode
    LLM_PROVIDER: str = "gemini" if os.getenv("GEMINI_API_KEY") else "opencode"
    
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    
    OPENCODE_BASE_URL: str = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/inference/openai/v1/chat/completions")
    OPENCODE_MODEL: str = os.getenv("OPENCODE_MODEL", "deepseek-v4.1-flash")
    
    # Model Roles (can be configured independently)
    ROUTER_MODEL: str = "gemini-3.5-flash-lite" if os.getenv("GEMINI_API_KEY") else "deepseek-v4.1-flash"
    VERIFIER_MODEL: str = "gemini-3.5-flash-lite" if os.getenv("GEMINI_API_KEY") else "deepseek-v4.1-flash"
    ANSWER_MODEL: str = "gemini-3.5-flash-lite" if os.getenv("GEMINI_API_KEY") else "deepseek-v4.1-flash"
    
    # Langfuse Settings
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    # Storage paths
    DATA_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    DOCUMENTS_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Train", "Documents"))
    BENCHMARKS_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Train", "Benchmarks", "benchmark_100.jsonl"))

settings = Settings()
