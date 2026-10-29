"""Nebius Token Factory client with per-call tracing (feeds the pipeline panel in the UI)."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .schemas import TraceStep

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

ROLES = ("nano", "super", "ultra", "vision")


def model_for(role: str) -> str:
    mid = os.getenv(f"MODEL_{role.upper()}", "").strip()
    if not mid:
        raise RuntimeError(f"MODEL_{role.upper()} is not set in backend/.env")
    return mid


_client: Optional[OpenAI] = None


def client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("NEBIUS_API_KEY", "").strip()
        if not key:
            raise RuntimeError("NEBIUS_API_KEY is not set in backend/.env")
        _client = OpenAI(api_key=key,
                         base_url=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"))
    return _client


def chat(role: str, messages: List[Dict[str, Any]], step: str, trace: List[TraceStep],
         **kwargs: Any) -> str:
    """One chat completion on the model mapped to `role`; appends a TraceStep."""
    model = model_for(role)
    t0 = time.perf_counter()
    resp = client().chat.completions.create(model=model, messages=messages, **kwargs)
    ms = int((time.perf_counter() - t0) * 1000)
    u = resp.usage
    trace.append(TraceStep(step=step, model=model, ms=ms,
                           tokens_in=getattr(u, "prompt_tokens", 0) or 0,
                           tokens_out=getattr(u, "completion_tokens", 0) or 0))
    return resp.choices[0].message.content or ""
