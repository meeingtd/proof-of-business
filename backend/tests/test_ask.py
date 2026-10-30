import json

import pytest
from fastapi.testclient import TestClient

from app import personas, underwriting as uw
from app.ask import ask_file
from app.main import app
from app.schemas import TraceStep

docs, rows, ASK, META = personas.generate("provisions-shop")
FACTS = uw.with_underwriting(rows, ASK)
F = {f.id: f.value for f in FACTS}


class FakeChat:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, role, messages, step, trace, **kw):
        self.calls.append((role, step))
        trace.append(TraceStep(step=step, model="fake-super"))
        r = self.replies.pop(0)
        return r if isinstance(r, str) else json.dumps(r)


def scenario(value=None):
    # sales fall by one third: stock falls with sales, other costs stay
    stock = "out_cat_stock_purchase / months_covered"
    expr = f"in_avg_month * 0.67 - ({stock} * 0.67 + (out_avg_month - {stock}))"
    real = F["in_avg_month"] * 0.67 - (F["out_cat_stock_purchase"] / 6 * 0.67 + (F["out_avg_month"] - F["out_cat_stock_purchase"] / 6))
    return {"answer": "Net cash flow would be about [[n1]] a month.",
            "numbers": [{"id": "n1", "value": real if value is None else value, "unit": "GHS", "calc": expr}]}


def test_uses_super_and_verifies_a_scenario_calc():
    chat = FakeChat(scenario())
    res = ask_file("What if sales fall by a third?", FACTS, ASK, "shop", [], chat_fn=chat)
    assert res.verifier.ok and chat.calls == [("super", "ask")]


def test_wrong_scenario_number_is_repaired():
    chat = FakeChat(scenario(value=99999), scenario())
    res = ask_file("What if sales fall by a third?", FACTS, ASK, "shop", [], chat_fn=chat)
    assert res.verifier.ok and [c[1] for c in chat.calls] == ["ask", "ask-repair"]


def test_cannot_answer_means_no_numbers():
    chat = FakeChat({"answer": "The records do not show the owner's rent.", "numbers": []})
    res = ask_file("What is the rent?", FACTS, ASK, "shop", [], chat_fn=chat)
    assert res.verifier.ok and res.numbers == []


def test_unfixable_answer_stays_flagged():
    chat = FakeChat(scenario(value=1), scenario(value=1))
    res = ask_file("What if sales fall by a third?", FACTS, ASK, "shop", [], chat_fn=chat)
    assert not res.verifier.ok


def test_endpoint_offline_scenario(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    c = TestClient(app)
    r = c.post("/demo/provisions-shop/ask", json={"question": "What happens if sales drop 30%?"}).json()
    assert r["mode"] == "offline" and r["verifier"]["blocked"] == [] and len(r["numbers"]) == 3
    r2 = c.post("/demo/provisions-shop/ask", json={"question": "Who is the owner's cousin?"}).json()
    assert r2["numbers"] == [] and r2["verifier"]["blocked"] == []
    assert c.post("/demo/provisions-shop/ask", json={"question": "  "}).status_code == 422
