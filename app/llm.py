"""
Unified LLM Client with structured JSON support, async concurrency, cost tracking,
and optional Langfuse observability. Supports Gemini 2.5 and OpenCode.
"""

import json
import time
import os
import re
import logging
from typing import Dict, Any, Optional, Tuple, List
import requests
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

# Token cost estimates per 1,000,000 tokens
MODEL_COSTS = {
    "gemini-flash-lite-latest": {"input": 0.075, "output": 0.30},
    "gemini-3.5-flash-lite": {"input": 0.05, "output": 0.20},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "deepseek-v4.1-flash": {"input": 0.14, "output": 0.28},
}

class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            self.api_key = settings.GEMINI_API_KEY
            self.base_url = settings.GEMINI_BASE_URL
            self.default_model = settings.GEMINI_MODEL
        else:
            self.api_key = settings.OPENCODE_API_KEY
            self.base_url = settings.OPENCODE_BASE_URL
            self.default_model = settings.OPENCODE_MODEL

        # Optional Langfuse client
        self.langfuse = None
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                from langfuse import Langfuse
                self.langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                logger.info("Langfuse tracing initialized.")
            except Exception as e:
                logger.warning(f"Langfuse init failed: {e}")

    @staticmethod
    def _safe_json_parse(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Fallback: extract first json object from curly braces
            m = re.search(r'(\{.*\})', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
            raise ValueError(f"Could not parse model output as JSON: {text[:500]}") from e

    def _calc_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        cost_info = MODEL_COSTS.get(model, {"input": 0.10, "output": 0.30})
        cost = (input_tokens / 1_000_000.0) * cost_info["input"] + (output_tokens / 1_000_000.0) * cost_info["output"]
        return round(cost, 6)

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        max_retries: int = 3
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Synchronous structured JSON call.
        Returns (parsed_dict, usage_metrics).
        """
        model_name = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        t0 = time.time()
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
                if resp.status_code == 402:
                    logger.warning(f"OpenCode returned 402 (Insufficient account funds). Falling back to secondary provider...")
                    if settings.GEMINI_API_KEY:
                        fb_headers = {"Authorization": f"Bearer {settings.GEMINI_API_KEY}", "Content-Type": "application/json"}
                        fb_payload = dict(payload)
                        fb_payload["model"] = settings.GEMINI_MODEL
                        fb_resp = requests.post(settings.GEMINI_BASE_URL, headers=fb_headers, json=fb_payload, timeout=60)
                        fb_resp.raise_for_status()
                        fb_data = fb_resp.json()
                        fb_content = fb_data["choices"][0]["message"]["content"]
                        parsed = self._safe_json_parse(fb_content)
                        return parsed, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_s": round(time.time() - t0, 3), "model": settings.GEMINI_MODEL}
                if resp.status_code == 429:
                    last_error = f"429 Too Many Requests: {resp.text}"
                    if ("per day" in resp.text.lower() or "perday" in resp.text.lower() or "daily" in resp.text.lower()) and "minute" not in resp.text.lower():
                        logger.warning("Daily quota exhausted. Failing fast to fallback.")
                        raise RuntimeError(last_error)
                    
                    # Extract suggested retryDelay if provided by Gemini
                    m_delay = re.search(r'"retryDelay":\s*"(\d+)s"', resp.text)
                    if m_delay:
                        sleep_time = min(float(m_delay.group(1)) + 1.0, 35.0)
                    else:
                        sleep_time = 4.0 * (attempt + 1)
                    logger.warning(f"Rate limited (429). Backing off for {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if not content:
                    raise ValueError(f"Empty content received from model: {data}")
                
                parsed = self._safe_json_parse(content)
                latency = round(time.time() - t0, 3)
                
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                cost = self._calc_cost(model_name, in_tok, out_tok)
                
                usage_dict = {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": cost,
                    "latency_s": latency,
                    "model": model_name,
                }
                return parsed, usage_dict
            except Exception as e:
                last_error = e
                time.sleep(2.0 * (attempt + 1))

        raise RuntimeError(f"LLM call_structured failed after {max_retries} attempts: {last_error}")

    def call_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        max_retries: int = 3
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Synchronous text call.
        Returns (raw_text, usage_metrics).
        """
        model_name = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        t0 = time.time()
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(self.base_url, headers=headers, json=payload, timeout=90)
                if resp.status_code == 402:
                    logger.warning("OpenCode returned 402 (Insufficient account funds). Falling back to secondary provider...")
                    if settings.GEMINI_API_KEY:
                        fb_headers = {"Authorization": f"Bearer {settings.GEMINI_API_KEY}", "Content-Type": "application/json"}
                        fb_payload = dict(payload)
                        fb_payload["model"] = settings.GEMINI_MODEL
                        fb_resp = requests.post(settings.GEMINI_BASE_URL, headers=fb_headers, json=fb_payload, timeout=90)
                        fb_resp.raise_for_status()
                        fb_data = fb_resp.json()
                        fb_content = fb_data["choices"][0]["message"]["content"]
                        return fb_content.strip(), {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_s": round(time.time() - t0, 3), "model": settings.GEMINI_MODEL}
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"] or ""
                latency = round(time.time() - t0, 3)
                
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                cost = self._calc_cost(model_name, in_tok, out_tok)
                
                usage_dict = {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": cost,
                    "latency_s": latency,
                    "model": model_name,
                }
                return content.strip(), usage_dict
            except Exception as e:
                last_error = e
                time.sleep(1.5 * (attempt + 1))

        raise RuntimeError(f"LLM call_text failed after {max_retries} attempts: {last_error}")

    async def acall_structured(
        self,
        client: httpx.AsyncClient,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        max_retries: int = 3
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Asynchronous structured JSON call for high-concurrency pipelines.
        """
        model_name = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        t0 = time.time()
        last_error = None
        import asyncio
        for attempt in range(max_retries):
            try:
                resp = await client.post(self.base_url, headers=headers, json=payload, timeout=60.0)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if not content:
                    raise ValueError(f"Empty content received from model: {data}")
                
                parsed = self._safe_json_parse(content)
                latency = round(time.time() - t0, 3)
                
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                cost = self._calc_cost(model_name, in_tok, out_tok)
                
                usage_dict = {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": cost,
                    "latency_s": latency,
                    "model": model_name,
                }
                return parsed, usage_dict
            except Exception as e:
                last_error = e
                await asyncio.sleep(1.5 * (attempt + 1))

        raise RuntimeError(f"Async LLM call failed after {max_retries} attempts: {last_error}")

# Global singleton client
default_llm_client = LLMClient()
