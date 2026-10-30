import pytest
from fastapi.testclient import TestClient

from app import personas
from app.main import app
from app.offline import MODEL_NAME
from app.pipeline import underwrite

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)


@pytest.mark.parametrize("slug,expected", [("fish-seller", "approve_smaller"),
                                           ("provisions-shop", "approve"), ("tailor", "decline")])
def test_offline_pipeline_verifies_every_number(slug, expected):
    docs, rows, ask, meta = personas.generate(slug)
    res = underwrite(docs, rows, ask, context=meta["name"], offline=True)
    assert res.verifier.ok and res.verifier.total >= 10
    assert res.memo.recommendation == expected
    assert [t.model for t in res.trace] == [MODEL_NAME]
    assert [s.title for s in res.memo.sections][0] == "Summary"


def test_personas_endpoint():
    r = client.get("/demo/personas")
    assert r.status_code == 200 and {p["slug"] for p in r.json()} == set(personas.SPECS)


def test_underwrite_endpoint_offline_when_no_key():
    r = client.post("/demo/fish-seller/underwrite", json={})
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "offline"
    assert body["verifier"]["blocked"] == [] and body["assumptions"]["rate_is_placeholder"] is True
    assert body["rows"] and body["docs"][0]["lines"]


def test_loan_ask_can_be_changed():
    small = client.post("/demo/fish-seller/underwrite", json={"amount": 1500}).json()
    assert small["memo"]["recommendation"] == "approve"
    big = client.post("/demo/provisions-shop/underwrite", json={"amount": 20000}).json()
    assert big["memo"]["recommendation"] in ("approve_smaller", "decline")


def test_unknown_persona_404():
    assert client.post("/demo/nobody/underwrite", json={}).status_code == 404


def test_tamper_is_caught_by_verify_endpoint():
    body = client.post("/demo/provisions-shop/underwrite", json={}).json()
    payload = {"memo": body["memo"], "facts": body["facts"]}
    assert client.post("/verify", json=payload).json()["blocked"] == []
    payload["memo"]["numbers"][1]["value"] += 500          # someone edits one figure
    out = client.post("/verify", json=payload).json()
    assert out["blocked"] and out["blocked"][0]["where"] == "n2"


def test_live_failure_is_an_error_not_a_silent_fallback(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "dummy")
    monkeypatch.delenv("MODEL_ULTRA", raising=False)
    r = client.post("/demo/fish-seller/underwrite", json={})
    assert r.status_code == 502


def test_plain_text_rendering_reads_cleanly():
    from app.verifier import render
    docs, rows, ask, meta = personas.generate("tailor")
    res = underwrite(docs, rows, ask, context=meta["name"], offline=True)
    text = " ".join(render(s.body, res.memo) for s in res.memo.sections)
    assert "months months" not in text and "GHS -" not in text and "[[" not in text
    assert "-GHS 49" in text and "0.03x" in text or "-0.03x" in text
