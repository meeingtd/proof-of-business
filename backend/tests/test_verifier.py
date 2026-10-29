from app.facts import build_facts
from app.schemas import LoanAsk, Memo, MemoNumber, MemoSection, Row
from app.verifier import safe_eval, verify, CalcError

import pytest

ROWS = [
    Row(id="r1", doc_id="d1", line=1, date="2026-08-03", amount=400, direction="in", counterparty="Customer A", category="sales"),
    Row(id="r2", doc_id="d1", line=2, date="2026-08-10", amount=600, direction="in", counterparty="Customer B", category="sales"),
    Row(id="r3", doc_id="d1", line=3, date="2026-08-12", amount=500, direction="out", counterparty="Supplier X", category="stock purchase"),
    Row(id="r4", doc_id="d1", line=4, date="2026-09-02", amount=1000, direction="in", counterparty="Customer A", category="sales"),
    Row(id="r5", doc_id="d1", line=5, date="2026-09-20", amount=300, direction="out", counterparty="Supplier X", category="stock purchase"),
]
FACTS = build_facts(ROWS, LoanAsk(amount=1200, tenor_months=6))
F = {f.id: f.value for f in FACTS}


def memo(numbers, body="Average monthly sales are [[n1]]."):
    return Memo(sections=[MemoSection(title="Cash flow", body=body)], numbers=numbers,
                recommendation="approve")


def test_facts_basic():
    assert F["in_total"] == 2000
    assert F["out_total"] == 800
    assert F["in_avg_month"] == 1000
    assert F["in_2026_09"] == 1000
    assert F["top_payer_share"] == 70.0       # Customer A: 1400 / 2000
    assert F["months_negative"] == 0


def test_correct_ref_passes():
    r = verify(memo([MemoNumber(id="n1", value=1000, unit="GHS", ref="in_avg_month")]), FACTS)
    assert r.ok and r.passed == 1 and r.total == 1


def test_planted_wrong_number_is_blocked():
    r = verify(memo([MemoNumber(id="n1", value=1500, unit="GHS", ref="in_avg_month")]), FACTS)
    assert not r.ok and "1500" in r.blocked[0].reason


def test_correct_calc_passes():
    # repayment cover: avg net per month / monthly instalment on a 6-month loan
    n = MemoNumber(id="n1", value=3.0, unit="ratio", calc="net_avg_month / (ask_amount / ask_tenor)")
    assert verify(memo([n]), FACTS).ok


def test_wrong_calc_blocked():
    n = MemoNumber(id="n1", value=5.0, unit="ratio", calc="net_avg_month / (ask_amount / ask_tenor)")
    assert not verify(memo([n]), FACTS).ok


def test_unknown_fact_blocked():
    r = verify(memo([MemoNumber(id="n1", value=1, unit="GHS", ref="profit_margin")]), FACTS)
    assert "unknown fact" in r.blocked[0].reason


def test_untagged_number_in_prose_blocked():
    m = memo([MemoNumber(id="n1", value=1000, unit="GHS", ref="in_avg_month")],
             body="Sales average [[n1]] and grew 25% last month.")
    r = verify(m, FACTS)
    assert any("untagged number '25'" in b.reason for b in r.blocked)


def test_missing_placeholder_blocked():
    r = verify(memo([], body="Sales are [[n9]]."), FACTS)
    assert any("[[n9]]" in b.reason for b in r.blocked)


def test_calc_rejects_code():
    with pytest.raises(CalcError):
        safe_eval("__import__('os').system('ls')", F)
    with pytest.raises(CalcError):
        safe_eval("in_total ** 2", F)
