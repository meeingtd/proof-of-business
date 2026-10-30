import pytest

from app import personas, underwriting as uw
from app.schemas import LoanAsk, Row

MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]


def make_rows(n_months, income, stock, other=0.0):
    """Simple book: `income` in, `stock` purchases and `other` fixed costs out, every month."""
    rows, i = [], 0

    def add(month, direction, amount, cat):
        nonlocal i
        i += 1
        rows.append(Row(id=f"r{i}", doc_id="d1", line=i, date=f"{month}-10", amount=amount,
                        direction=direction, counterparty="X", category=cat))

    for m in MONTHS[:n_months]:
        add(m, "in", income, "sales")
        add(m, "out", stock, "stock purchase")
        if other:
            add(m, "out", other, "transport")
    return rows


def run(rows, ask, rate=0.30):
    facts = uw.with_underwriting(rows, ask, rate)
    return {x.id: x.value for x in facts}, uw.decide(facts, ask)


def test_instalment_formula():
    # 6000 over 6 months at 30% flat: interest 900, instalment 1150
    assert uw.instalment(6000, 6, 0.30) == pytest.approx(1150)
    assert uw.amount_for_instalment(1150, 6, 0.30) == pytest.approx(6000)


def test_approve():
    # net 1000/month, stress-proof; loan 3000 -> instalment 575 -> cover 1.74
    f, rec = run(make_rows(6, 2000, 1000), LoanAsk(amount=3000, tenor_months=6))
    assert f["instalment"] == pytest.approx(575)
    assert f["cover"] == pytest.approx(1000 / 575, abs=0.01)
    assert rec == "approve"


def test_approve_smaller_when_cover_between_1_and_1_5():
    # instalment 575 vs net 700 -> cover 1.22
    f, rec = run(make_rows(6, 2000, 1300), LoanAsk(amount=3000, tenor_months=6))
    assert 1.0 <= f["cover"] < 1.5 and rec == "approve_smaller"
    assert 0 < f["max_amount"] < 3000


def test_approve_smaller_when_stress_fails_even_if_cover_ok():
    # high fixed cost: net 900 passes 1.5x on a 575 instalment, but a 20% sales drop wipes it out
    f, rec = run(make_rows(6, 3000, 600, other=1500), LoanAsk(amount=3000, tenor_months=6))
    assert f["cover"] >= 1.5 and f["stress_cover"] < 1.0
    assert rec == "approve_smaller" and f["max_amount"] < 3000


def test_decline_when_cover_below_1():
    f, rec = run(make_rows(6, 2000, 1500), LoanAsk(amount=3000, tenor_months=6))
    assert f["cover"] < 1.0 and rec == "decline"


def test_decline_when_no_cash_flow():
    _, rec = run(make_rows(6, 2000, 2100), LoanAsk(amount=1000, tenor_months=6))
    assert rec == "decline"


def test_need_more_info_under_three_months():
    _, rec = run(make_rows(2, 2000, 1000), LoanAsk(amount=1000, tenor_months=6))
    assert rec == "need_more_info"


def test_need_more_info_without_an_ask():
    _, rec = run(make_rows(6, 2000, 1000), None)
    assert rec == "need_more_info"


def test_max_amount_lands_exactly_on_the_target():
    rows = make_rows(6, 2000, 1300)
    f, _ = run(rows, LoanAsk(amount=3000, tenor_months=6))
    f2, rec2 = run(rows, LoanAsk(amount=f["max_amount"], tenor_months=6))
    assert f2["cover"] == pytest.approx(1.5, abs=0.02) and rec2 == "approve"


def test_higher_rate_means_lower_cover():
    rows = make_rows(6, 2000, 1000)
    a, _ = run(rows, LoanAsk(amount=3000, tenor_months=6), 0.10)
    b, _ = run(rows, LoanAsk(amount=3000, tenor_months=6), 0.50)
    assert b["instalment"] > a["instalment"] and b["cover"] < a["cover"]


def test_personas_give_three_different_answers():
    got = {}
    for slug in personas.SPECS:
        _, rows, ask, _ = personas.generate(slug)
        got[slug] = run(rows, ask)[1]
    assert got == {"fish-seller": "approve_smaller", "provisions-shop": "approve", "tailor": "decline"}
