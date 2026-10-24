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
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "opencode" if os.getenv("OPENCODE_API_KEY") else "gemini")
    
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    
    OPENCODE_BASE_URL: str = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/inference/openai/v1/chat/completions")
    OPENCODE_MODEL: str = os.getenv("OPENCODE_MODEL", "deepseek-v4.1-flash")
    
    # Model Roles
    ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "deepseek-v4.1-flash" if os.getenv("LLM_PROVIDER") == "opencode" else "gemini-flash-lite-latest")
    VERIFIER_MODEL: str = os.getenv("VERIFIER_MODEL", "deepseek-v4.1-flash" if os.getenv("LLM_PROVIDER") == "opencode" else "gemini-flash-lite-latest")
    ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "deepseek-v4.1-flash" if os.getenv("LLM_PROVIDER") == "opencode" else "gemini-flash-lite-latest")
    
    # Langfuse Settings
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    # Storage paths
    DATA_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    DOCUMENTS_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Train", "Documents"))
    BENCHMARKS_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Train", "Benchmarks", "benchmark_100.jsonl"))

settings = Settings()
