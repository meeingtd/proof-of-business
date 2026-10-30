import json

import pytest

from app import personas, underwriting as uw
from app.memo import MemoError, generate_memo
from app.schemas import TraceStep

docs, rows, ASK, META = personas.generate("provisions-shop")
FACTS = uw.with_underwriting(rows, ASK)
F = {f.id: f.value for f in FACTS}


def good_memo(**over):
    memo = {
        "sections": [
            {"title": "Summary", "body": "Money in averages [[n1]] a month and the loan costs [[n2]] a month."},
            {"title": "Repayment capacity", "body": "Cover is [[n3]] against a target of [[n4]]."},
        ],
        "numbers": [
            {"id": "n1", "value": F["in_avg_month"], "unit": "GHS", "ref": "in_avg_month"},
            {"id": "n2", "value": F["instalment"], "unit": "GHS", "ref": "instalment"},
            {"id": "n3", "value": F["cover"], "unit": "ratio", "ref": "cover"},
            {"id": "n4", "value": 1.5, "unit": "ratio", "calc": "cover_target"},
        ],
        "recommendation": "approve",
    }
    memo.update(over)
    return memo


class FakeChat:
    """Stands in for tf_client.chat; replies in order and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, role, messages, step, trace, **kw):
        self.calls.append((role, step, messages))
        trace.append(TraceStep(step=step, model="fake-ultra", tokens_in=10, tokens_out=20, ms=5))
        r = self.replies.pop(0)
        return r if isinstance(r, str) else json.dumps(r)


def test_clean_memo_passes_with_one_call():
    chat, trace = FakeChat(good_memo()), []
    memo, result = generate_memo(FACTS, ASK, "shop", trace, chat_fn=chat)
    assert result.ok and result.passed == result.total == 4
    assert len(chat.calls) == 1 and chat.calls[0][0] == "ultra"
    assert [t.step for t in trace] == ["memo"]


def test_prompt_contains_facts_and_the_decision():
    chat = FakeChat(good_memo())
    generate_memo(FACTS, ASK, "shop", [], chat_fn=chat)
    user = chat.calls[0][2][1]["content"]
    assert "in_avg_month |" in user and "RECOMMENDATION (decided by rules, state it): approve" in user


def test_wrong_number_triggers_one_repair_that_fixes_it():
    bad = good_memo()
    bad["numbers"][0]["value"] = F["in_avg_month"] * 1.4
    chat, trace = FakeChat(bad, good_memo()), []
    memo, result = generate_memo(FACTS, ASK, "shop", trace, chat_fn=chat)
    assert result.ok
    assert [t.step for t in trace] == ["memo", "repair"]
    repair_prompt = chat.calls[1][2][-1]["content"]
    assert "n1" in repair_prompt and "in_avg_month" in repair_prompt


def test_repair_that_still_fails_keeps_the_blocked_numbers_visible():
    bad = good_memo()
    bad["numbers"][0]["value"] = 1.0
    chat = FakeChat(bad, bad)
    memo, result = generate_memo(FACTS, ASK, "shop", [], chat_fn=chat)
    assert not result.ok and result.passed == 3 and result.total == 4
    assert result.blocked[0].where == "n1"
    assert len(memo.numbers) == 4          # nothing hidden


def test_untagged_digits_are_caught():
    bad = good_memo()
    bad["sections"][0]["body"] += " Sales grew 25% in July."
    chat = FakeChat(bad, good_memo())
    _, result = generate_memo(FACTS, ASK, "shop", [], chat_fn=chat)
    assert result.ok and "untagged number '25'" in chat.calls[1][2][-1]["content"]


def test_rules_override_the_models_recommendation():
    memo, _ = generate_memo(FACTS, ASK, "shop", [], chat_fn=FakeChat(good_memo(recommendation="decline")))
    assert memo.recommendation == "approve"


def test_handles_fences_and_reasoning_text():
    wrapped = "<think>let me work it out {not json}</think>\n```json\n" + json.dumps(good_memo()) + "\n```"
    _, result = generate_memo(FACTS, ASK, "shop", [], chat_fn=FakeChat(wrapped))
    assert result.ok


def test_unparseable_twice_raises():
    with pytest.raises(MemoError):
        generate_memo(FACTS, ASK, "shop", [], chat_fn=FakeChat("sorry, I cannot", "still no"))


def test_repair_can_be_turned_off():
    bad = good_memo()
    bad["numbers"][0]["value"] = 1.0
    chat = FakeChat(bad)
    _, result = generate_memo(FACTS, ASK, "shop", [], chat_fn=chat, repair=False)
    assert not result.ok and len(chat.calls) == 1
