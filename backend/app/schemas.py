"""Shared contract between ingestion (Joel) and underwriting/UI (Julian).

Flow: documents -> rows (Nano / vision extraction) -> facts (deterministic)
-> memo (Ultra, cites facts) -> verifier (deterministic) -> UI.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Doc(BaseModel):
    id: str                      # "d1"
    kind: Literal["statement", "receipt", "chat", "other"]
    name: str                    # original file name (masked if needed)
    lines: List[str] = []        # text lines after OCR/parse and PII masking


class Row(BaseModel):
    """One money movement. Every row must point back to a doc line."""
    id: str                      # "r1"
    doc_id: str
    line: int                    # index into Doc.lines
    date: str                    # YYYY-MM-DD
    amount: float                # always positive, in GHS
    direction: Literal["in", "out"]
    counterparty: str = ""       # masked, e.g. "Customer A7"
    category: str = ""           # "sales", "stock purchase", "transport", "personal", ...


class Fact(BaseModel):
    """A number computed in Python from rows. The only numbers Ultra may cite."""
    id: str                      # valid Python name, e.g. "in_avg_month"
    label: str
    value: float
    unit: Literal["GHS", "count", "pct", "months", "ratio"]
    rows: List[str] = []         # row ids this fact was computed from


class MemoNumber(BaseModel):
    """A number that appears in the memo. Exactly one of ref / calc."""
    id: str                      # "n1"; prose refers to it as [[n1]]
    value: float
    unit: str
    ref: Optional[str] = None    # a Fact id
    calc: Optional[str] = None   # arithmetic over Fact ids, e.g. "in_avg_month * 0.3"


class MemoSection(BaseModel):
    title: str
    body: str                    # prose; every number must be a [[nX]] placeholder


class Memo(BaseModel):
    sections: List[MemoSection]
    numbers: List[MemoNumber]
    recommendation: Literal["approve", "approve_smaller", "decline", "need_more_info"]


class Blocked(BaseModel):
    where: str                   # number id or section title
    reason: str


class VerifierResult(BaseModel):
    passed: int
    total: int
    blocked: List[Blocked] = []

    @property
    def ok(self) -> bool:
        return not self.blocked


class TraceStep(BaseModel):
    step: str                    # "extract", "vision", "memo", "repair", "ask", ...
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0


class LoanAsk(BaseModel):
    amount: Optional[float] = None   # GHS
    purpose: str = ""
    tenor_months: Optional[int] = None


class AnalyzeResponse(BaseModel):
    docs: List[Doc]
    rows: List[Row]
    facts: List[Fact]
    memo: Optional[Memo] = None
    verifier: Optional[VerifierResult] = None
    trace: List[TraceStep] = Field(default_factory=list)
