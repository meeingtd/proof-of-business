"""The seam between ingestion (Joel) and underwriting (Julian).

Joel's /analyze extracts docs and rows, then calls underwrite(). His proof layer wraps the result.
"""
from __future__ import annotations

from typing import List, Optional

from .memo import ChatFn, generate_memo
from .offline import make_offline_chat
from .schemas import AnalyzeResponse, Doc, LoanAsk, Row, TraceStep
from .underwriting import DEFAULT_ANNUAL_RATE, with_underwriting


def underwrite(docs: List[Doc], rows: List[Row], ask: Optional[LoanAsk], context: str = "",
               annual_rate: float = DEFAULT_ANNUAL_RATE, chat_fn: Optional[ChatFn] = None,
               offline: bool = False, trace: Optional[List[TraceStep]] = None) -> AnalyzeResponse:
    """rows -> facts -> Ultra memo -> verifier. `trace` may already hold Joel's extraction steps."""
    trace = trace if trace is not None else []
    facts = with_underwriting(rows, ask, annual_rate)
    if offline:
        chat_fn = make_offline_chat(facts, ask, context)
    memo, verifier = generate_memo(facts, ask, context, trace, chat_fn=chat_fn)
    return AnalyzeResponse(docs=docs, rows=rows, facts=facts, memo=memo, verifier=verifier, trace=trace)
