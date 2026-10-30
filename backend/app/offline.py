"""Offline stand-in for Ultra, used ONLY when there is no Token Factory key (UI development, tests).

It writes the same JSON shape Ultra must, from a fixed template over the same facts, so the whole
pipeline (verifier, UI, source chips) can be exercised. It is never a Nemotron call, and its trace
steps say so. The final demo and submission must run live.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, List

from .schemas import Fact, TraceStep
from .underwriting import decide

MODEL_NAME = "offline-template (no Nebius call)"

RESULT_TEXT = {
    "approve": "the loan can be approved as asked",
    "approve_smaller": "a smaller loan can be approved",
    "decline": "the loan should be declined at this time",
    "need_more_info": "more information is needed before deciding",
}


def make_offline_chat(facts: List[Fact], ask, context: str) -> Callable[..., str]:
    f: Dict[str, float] = {x.id: x.value for x in facts}
    unit = {x.id: x.unit for x in facts}
    decision = decide(facts, ask)

    def chat(role, messages, step, trace, **kw) -> str:
        numbers: List[dict] = []

        def n(ref: str) -> str:
            nid = f"n{len(numbers) + 1}"
            numbers.append({"id": nid, "value": f[ref], "unit": unit[ref], "ref": ref})
            return f"[[{nid}]]"

        def calc(expr: str, value: float, u: str) -> str:
            nid = f"n{len(numbers) + 1}"
            numbers.append({"id": nid, "value": round(value, 2), "unit": u, "calc": expr})
            return f"[[{nid}]]"

        has = lambda *ids: all(i in f for i in ids)  # noqa: E731

        summary = (f"{context}. The records cover {n('months_covered')} months. Money in averages "
                   f"{n('in_avg_month')} a month. After costs and personal withdrawals, net cash flow averages "
                   f"{n('net_avg_month')} a month. On the lender's rules, {RESULT_TEXT[decision]}.")

        flow = (f"The best month brought in {n('in_best_month')} and the weakest {n('in_worst_month')}. "
                f"Net cash flow was negative in {n('months_negative')} of {n('months_covered')} months.")

        cust = []
        if has("top_payer_share", "top3_payer_share", "payers_distinct"):
            cust.append(f"{n('payers_distinct')} different customers paid in. The largest one accounts for "
                        f"{n('top_payer_share')} of money in and the three largest for {n('top3_payer_share')}.")
        if has("out_cat_personal", "out_total"):
            share = 100 * f["out_cat_personal"] / f["out_total"]
            cust.append("Personal withdrawals are "
                        + calc("out_cat_personal / out_total * 100", share, "pct")
                        + " of all money out, which reduces what is available for repayment.")
        if not cust:
            cust.append("The records do not show enough counterparty detail to assess customer concentration.")

        if has("instalment", "cover", "stress_cover"):
            cap = (f"The loan asked for is {n('ask_amount')} over {n('ask_tenor')} months at an assumed "
                   f"{n('ask_rate')} flat annual rate, which is {n('instalment')} a month. Repayment cover "
                   f"(average net cash flow divided by the instalment) is {n('cover')} against a requirement of "
                   f"{n('cover_target')}. If sales fell by one fifth, cover would be {n('stress_cover')}.")
        else:
            cap = "No loan amount or term was given, so repayment capacity could not be tested."

        risks = []
        if has("months_negative") and f["months_negative"] >= 1:
            risks.append("At least one month lost money, so the business cannot be assumed to cover repayments every month.")
        if has("top_payer_share") and f["top_payer_share"] >= 30:
            risks.append("One customer provides a large share of income; losing them would hurt quickly.")
        if has("stress_cover") and f["stress_cover"] < 1.0:
            risks.append("A modest fall in sales would leave too little cash to meet the instalment.")
        if has("out_cat_personal", "out_total") and f["out_cat_personal"] / f["out_total"] > 0.2:
            risks.append("Personal withdrawals take a sizeable part of the cash that comes in.")
        if not risks:
            risks.append("No major warning signs appear in these records.")

        rec = {
            "approve": "Approve the loan as asked.",
            "approve_smaller": ("Approve a smaller loan, up to " + n("max_amount") + "."
                                if has("max_amount") else "Approve a smaller loan."),
            "decline": "Decline for now. Cash flow does not support the repayments.",
            "need_more_info": "Collect more records before deciding.",
        }[decision]

        memo = {
            "sections": [
                {"title": "Summary", "body": summary},
                {"title": "Cash flow", "body": flow},
                {"title": "Customers and costs", "body": " ".join(cust)},
                {"title": "Repayment capacity", "body": cap},
                {"title": "Risks", "body": " ".join(risks)},
                {"title": "Recommendation", "body": rec},
            ],
            "numbers": numbers,
            "recommendation": decision,
        }
        trace.append(TraceStep(step=step, model=MODEL_NAME, tokens_in=0, tokens_out=0, ms=0))
        return json.dumps(memo)

    return chat
