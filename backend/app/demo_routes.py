"""Demo API for the web app: the three synthetic traders, plus a standalone /verify for the tamper demo."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import personas
from .ask import AskResult, ask_file, make_offline_ask
from .pipeline import underwrite
from .schemas import AnalyzeResponse, Fact, LoanAsk, Memo, VerifierResult
from .underwriting import (COVER_TARGET, DEFAULT_ANNUAL_RATE, MIN_MONTHS, RATE_SOURCE, STRESS_DROP,
                           STRESS_MIN_COVER, with_underwriting)
from .verifier import verify

router = APIRouter()


class UnderwriteRequest(BaseModel):
    amount: Optional[float] = None
    tenor_months: Optional[int] = None
    purpose: Optional[str] = None
    annual_rate: Optional[float] = None      # 0.30 means 30% flat per year
    offline: bool = False                    # force the offline template even if a key exists


class DemoResponse(AnalyzeResponse):
    meta: dict
    assumptions: dict
    mode: str                                # "live" (Token Factory) or "offline" (template, no model call)


class VerifyRequest(BaseModel):
    memo: Memo
    facts: List[Fact]


def has_key() -> bool:
    return bool(os.getenv("NEBIUS_API_KEY", "").strip())


@router.get("/demo/personas")
def list_personas():
    out = []
    for slug in personas.SPECS:
        _, _, ask, meta = personas.load(slug)
        out.append({**meta, "ask": ask.model_dump()})
    return out


@router.post("/demo/{slug}/underwrite", response_model=DemoResponse)
def underwrite_persona(slug: str, req: UnderwriteRequest):
    if slug not in personas.SPECS:
        raise HTTPException(404, f"unknown persona '{slug}'")
    docs, rows, base_ask, meta = personas.load(slug)
    ask = LoanAsk(amount=req.amount if req.amount is not None else base_ask.amount,
                  purpose=req.purpose if req.purpose is not None else base_ask.purpose,
                  tenor_months=req.tenor_months if req.tenor_months is not None else base_ask.tenor_months)
    rate = req.annual_rate if req.annual_rate is not None else DEFAULT_ANNUAL_RATE
    offline = req.offline or not has_key()
    context = f"{meta['name']}, {meta['business'].lower()}, {meta['location']}"
    try:
        res = underwrite(docs, rows, ask, context=context, annual_rate=rate, offline=offline)
    except RuntimeError as e:   # live call failed: say so, never quietly fall back to the template
        raise HTTPException(502, f"Token Factory step failed: {e}")
    return DemoResponse(
        **res.model_dump(), meta=meta, mode="offline" if offline else "live",
        assumptions={"annual_rate": rate, "rate_source": RATE_SOURCE, "rate_is_default": req.annual_rate is None, "cover_target": COVER_TARGET,
                     "stress_drop": STRESS_DROP, "stress_min_cover": STRESS_MIN_COVER,
                     "min_months": MIN_MONTHS, "ask": ask.model_dump()})


@router.post("/verify", response_model=VerifierResult)
def verify_memo(req: VerifyRequest):
    """Re-run the verifier on a (possibly edited) memo. Powers the tamper demo."""
    return verify(req.memo, req.facts)


class AskRequest(UnderwriteRequest):
    question: str


class AskResponse(AskResult):
    mode: str


@router.post("/demo/{slug}/ask", response_model=AskResponse)
def ask_persona(slug: str, req: AskRequest):
    if slug not in personas.SPECS:
        raise HTTPException(404, f"unknown persona '{slug}'")
    if not req.question.strip():
        raise HTTPException(422, "question is empty")
    _, rows, base_ask, meta = personas.load(slug)
    ask = LoanAsk(amount=req.amount if req.amount is not None else base_ask.amount,
                  purpose=base_ask.purpose,
                  tenor_months=req.tenor_months if req.tenor_months is not None else base_ask.tenor_months)
    facts = with_underwriting(rows, ask, req.annual_rate if req.annual_rate is not None else DEFAULT_ANNUAL_RATE)
    offline = req.offline or not has_key()
    context = f"{meta['name']}, {meta['business'].lower()}, {meta['location']}"
    try:
        res = ask_file(req.question, facts, ask, context, [],
                       chat_fn=make_offline_ask(facts, req.question) if offline else None)
    except RuntimeError as e:
        raise HTTPException(502, f"Token Factory step failed: {e}")
    return AskResponse(**res.model_dump(), mode="offline" if offline else "live")
