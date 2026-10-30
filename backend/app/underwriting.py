"""Repayment math and the approve / smaller / decline rule. All deterministic Python.

The model never decides the recommendation or does arithmetic: it explains these facts.
Terms Julian set (2026-10-29): 1.5x cover target, 20% sales-drop stress that must stay >= 1.0x,
at least 3 months of history, flat annual interest rate the loan officer can edit.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .facts import build_facts
from .schemas import Fact, LoanAsk, Row

COVER_TARGET = 1.5
STRESS_DROP = 0.20
STRESS_MIN_COVER = 1.0
MIN_MONTHS = 3
# PLACEHOLDER until a sourced typical Ghana microfinance rate is in research/. Shown as an
# assumption in the UI and not quoted in the pitch.
DEFAULT_ANNUAL_RATE = 0.30

STOCK_FACT = "out_cat_stock_purchase"


def _r(x: float) -> float:
    return round(x, 2)


def instalment(amount: float, tenor_months: int, annual_rate: float) -> float:
    """Flat-rate instalment: interest is charged on the original principal."""
    return amount * (1 + annual_rate * tenor_months / 12) / tenor_months


def amount_for_instalment(inst: float, tenor_months: int, annual_rate: float) -> float:
    return inst * tenor_months / (1 + annual_rate * tenor_months / 12)


def underwriting_facts(base: List[Fact], ask: Optional[LoanAsk],
                       annual_rate: float = DEFAULT_ANNUAL_RATE) -> List[Fact]:
    f: Dict[str, float] = {x.id: x.value for x in base}
    out: List[Fact] = []

    def add(id: str, label: str, value: float, unit: str) -> None:
        out.append(Fact(id=id, label=label, value=_r(value), unit=unit, rows=[]))

    months = max(f.get("months_covered", 0), 1)
    in_avg = f.get("in_avg_month", 0.0)
    out_avg = f.get("out_avg_month", 0.0)
    net_avg = f.get("net_avg_month", 0.0)
    stock_avg = f.get(STOCK_FACT, 0.0) / months   # the cost that moves with sales
    # Stress: sales fall, stock purchases fall with them, every other cost stays.
    stress_net = (1 - STRESS_DROP) * in_avg - ((1 - STRESS_DROP) * stock_avg + (out_avg - stock_avg))

    add("stress_net_avg_month", f"Net cash flow per month if sales fall {int(STRESS_DROP * 100)}%",
        stress_net, "GHS")
    add("cover_target", "Repayment cover the lender requires", COVER_TARGET, "ratio")

    if ask and ask.amount and ask.tenor_months:
        t = ask.tenor_months
        inst = instalment(ask.amount, t, annual_rate)
        add("ask_rate", "Assumed flat annual interest rate", annual_rate * 100, "pct")
        add("instalment", "Monthly instalment on the loan asked for", inst, "GHS")
        add("cover", "Repayment cover (average net cash flow / instalment)", net_avg / inst, "ratio")
        add("stress_cover", "Repayment cover if sales fall 20%", stress_net / inst, "ratio")
        cap = min(net_avg / COVER_TARGET, stress_net / STRESS_MIN_COVER)
        add("max_amount", "Largest loan that meets the cover target and the stress test",
            max(0.0, amount_for_instalment(cap, t, annual_rate)), "GHS")
    return out


def with_underwriting(rows: List[Row], ask: Optional[LoanAsk],
                      annual_rate: float = DEFAULT_ANNUAL_RATE) -> List[Fact]:
    base = build_facts(rows, ask)
    return base + underwriting_facts(base, ask, annual_rate)


def decide(facts: List[Fact], ask: Optional[LoanAsk]) -> str:
    f = {x.id: x.value for x in facts}
    if f.get("months_covered", 0) < MIN_MONTHS or "cover" not in f:
        return "need_more_info"
    cover, stress, max_amount = f["cover"], f["stress_cover"], f["max_amount"]
    if cover >= COVER_TARGET and stress >= STRESS_MIN_COVER:
        return "approve"
    if cover >= 1.0 and max_amount > 0:
        return "approve_smaller"
    return "decline"
