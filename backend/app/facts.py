"""Deterministic facts from extracted rows. Ultra cites these; it never does its own sums."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .schemas import Fact, LoanAsk, Row


def _r(x: float) -> float:
    return round(x, 2)


def build_facts(rows: List[Row], ask: Optional[LoanAsk] = None) -> List[Fact]:
    facts: List[Fact] = []

    def add(id: str, label: str, value: float, unit: str, row_ids: List[str]) -> None:
        facts.append(Fact(id=id, label=label, value=_r(value), unit=unit, rows=row_ids))

    ins = [r for r in rows if r.direction == "in"]
    outs = [r for r in rows if r.direction == "out"]
    all_ids = [r.id for r in rows]

    by_month_in: Dict[str, List[Row]] = defaultdict(list)
    by_month_out: Dict[str, List[Row]] = defaultdict(list)
    for r in ins:
        by_month_in[r.date[:7]].append(r)
    for r in outs:
        by_month_out[r.date[:7]].append(r)
    months = sorted(set(by_month_in) | set(by_month_out))
    n_months = max(len(months), 1)

    total_in = sum(r.amount for r in ins)
    total_out = sum(r.amount for r in outs)
    add("months_covered", "Months of history", len(months), "months", all_ids)
    add("tx_count", "Transactions", len(rows), "count", all_ids)
    add("in_total", "Total money in", total_in, "GHS", [r.id for r in ins])
    add("out_total", "Total money out", total_out, "GHS", [r.id for r in outs])
    add("net_total", "Net cash flow", total_in - total_out, "GHS", all_ids)
    add("in_avg_month", "Average money in per month", total_in / n_months, "GHS", [r.id for r in ins])
    add("out_avg_month", "Average money out per month", total_out / n_months, "GHS", [r.id for r in outs])
    add("net_avg_month", "Average net cash flow per month", (total_in - total_out) / n_months, "GHS", all_ids)

    month_net = {}
    for m in months:
        mi, mo = by_month_in.get(m, []), by_month_out.get(m, [])
        key = m.replace("-", "_")
        si, so = sum(r.amount for r in mi), sum(r.amount for r in mo)
        month_net[m] = si - so
        add(f"in_{key}", f"Money in, {m}", si, "GHS", [r.id for r in mi])
        add(f"out_{key}", f"Money out, {m}", so, "GHS", [r.id for r in mo])
        add(f"net_{key}", f"Net cash flow, {m}", si - so, "GHS", [r.id for r in mi + mo])

    if months:
        month_in = {m: sum(r.amount for r in by_month_in.get(m, [])) for m in months}
        best = max(months, key=lambda m: month_in[m])
        worst = min(months, key=lambda m: month_in[m])
        add("in_best_month", f"Best month for money in ({best})", month_in[best],
            "GHS", [r.id for r in by_month_in.get(best, [])])
        add("in_worst_month", f"Weakest month for money in ({worst})", month_in[worst],
            "GHS", [r.id for r in by_month_in.get(worst, [])])
        neg = [m for m in months if month_net[m] < 0]
        add("months_negative", "Months with negative net cash flow", len(neg), "count",
            [r.id for m in neg for r in by_month_in.get(m, []) + by_month_out.get(m, [])])

    sales = [r for r in ins if r.category == "sales"] or ins
    if sales:
        add("sales_count", "Number of sales receipts", len(sales), "count", [r.id for r in sales])
        add("avg_ticket", "Average sale", sum(r.amount for r in sales) / len(sales), "GHS",
            [r.id for r in sales])
        biggest = max(sales, key=lambda r: r.amount)
        add("largest_in", "Largest single payment in", biggest.amount, "GHS", [biggest.id])

    by_cp: Dict[str, List[Row]] = defaultdict(list)
    for r in ins:
        if r.counterparty:
            by_cp[r.counterparty].append(r)
    if by_cp and total_in > 0:
        ranked = sorted(by_cp.items(), key=lambda kv: -sum(r.amount for r in kv[1]))
        top_rows = ranked[0][1]
        top3_rows = [r for _, rs in ranked[:3] for r in rs]
        add("payers_distinct", "Distinct paying customers", len(by_cp), "count", [r.id for r in ins])
        add("top_payer_share", "Share of money in from the largest payer",
            100 * sum(r.amount for r in top_rows) / total_in, "pct", [r.id for r in top_rows])
        add("top3_payer_share", "Share of money in from the 3 largest payers",
            100 * sum(r.amount for r in top3_rows) / total_in, "pct", [r.id for r in top3_rows])

    by_cat: Dict[str, List[Row]] = defaultdict(list)
    for r in outs:
        by_cat[r.category or "other"].append(r)
    for cat, rs in sorted(by_cat.items()):
        key = "".join(c if c.isalnum() else "_" for c in cat.lower())
        add(f"out_cat_{key}", f"Money out on {cat}", sum(r.amount for r in rs), "GHS", [r.id for r in rs])

    if ask and ask.amount:
        add("ask_amount", "Loan amount requested", ask.amount, "GHS", [])
        if ask.tenor_months:
            add("ask_tenor", "Requested tenor", ask.tenor_months, "months", [])

    return facts
