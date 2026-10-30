"""Credit memo from Nemotron Ultra, held to the verifier.

Ultra explains; it does not compute or decide. Every number it writes must be a [[nX]]
placeholder tied to a fact (`ref`) or arithmetic over facts (`calc`). The recommendation is
set by underwriting.decide() and overwrites whatever the model says.
"""
from __future__ import annotations

import json
import re
from typing import Callable, List, Optional, Tuple

from pydantic import ValidationError

from . import tf_client
from .schemas import Fact, LoanAsk, Memo, TraceStep, VerifierResult
from .underwriting import decide
from .verifier import verify

ChatFn = Callable[..., str]

SYSTEM = """You are a credit analyst writing a one-page credit file for a microfinance loan officer in Ghana, \
about a small informal business. You are given FACTS that were computed from the business's own mobile-money \
records. Write only from those facts.

HARD RULES
1. Never write a digit in prose. Every number, amount, percentage, count and duration (even "six months" or \
"20%") must be a placeholder like [[n1]] in the text.
2. Every placeholder needs an entry in "numbers": {"id": "n1", "value": <number>, "unit": "<GHS|pct|count|months|ratio>", \
and exactly one of "ref" (a fact id, value copied exactly) or "calc" (arithmetic over fact ids using + - * / ( ) only)}.
3. Use only fact ids from the list. Do not invent figures. If a fact you need is missing, say so in words.
4. Write months by name only ("July"), never with a year or a date.
5. The recommendation is already decided by the lender's rules. State it and explain it from the facts; do not argue with it.
6. Plain, direct language. Name real risks (a slow month, one dominant customer, personal withdrawals) when the facts show them.

Return ONLY a JSON object, no commentary:
{"sections":[{"title":"...","body":"..."}], "numbers":[...], "recommendation":"<given>"}
Sections, in order: "Summary", "Cash flow", "Customers and costs", "Repayment capacity", "Risks", "Recommendation"."""

REPAIR = """Your memo failed verification. Fix ONLY these problems and return the complete JSON again:
{problems}

Reminders: no digits in prose (use [[nX]] placeholders), copy fact values exactly, use only listed fact ids."""


class MemoError(RuntimeError):
    pass


def _facts_block(facts: List[Fact]) -> str:
    return "\n".join(f"{f.id} | {f.label} | {f.value:g} {f.unit}" for f in facts)


def _extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def _parse(text: str) -> Memo:
    try:
        return Memo.model_validate(_extract_json(text))
    except (ValueError, ValidationError) as e:
        raise ValueError(f"reply was not a valid memo: {str(e)[:300]}")


def generate_memo(facts: List[Fact], ask: Optional[LoanAsk], context: str, trace: List[TraceStep],
                  chat_fn: Optional[ChatFn] = None, repair: bool = True) -> Tuple[Memo, VerifierResult]:
    chat = chat_fn or tf_client.chat
    decision = decide(facts, ask)
    purpose = f" Purpose: {ask.purpose}." if ask and ask.purpose else ""
    user = (f"BUSINESS: {context}\nLOAN ASKED:{purpose}\nRECOMMENDATION (decided by rules, state it): {decision}\n\n"
            f"FACTS (id | label | value):\n{_facts_block(facts)}")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]

    reply = chat("ultra", messages, step="memo", trace=trace, temperature=0.2, max_tokens=6000)
    last_error = ""
    memo: Optional[Memo] = None
    result: Optional[VerifierResult] = None
    for attempt in range(2 if repair else 1):
        try:
            memo = _parse(reply)
        except ValueError as e:
            problems = str(e)
            last_error = problems
        else:
            memo.recommendation = decision   # the rules decide, not the model
            result = verify(memo, facts)
            if result.ok:
                return memo, result
            problems = "\n".join(f"- {b.where}: {b.reason}" for b in result.blocked)
        if attempt == 0 and repair:
            messages = messages + [{"role": "assistant", "content": reply},
                                   {"role": "user", "content": REPAIR.format(problems=problems)}]
            reply = chat("ultra", messages, step="repair", trace=trace, temperature=0.1, max_tokens=6000)
    if memo is None or result is None:
        raise MemoError(last_error or "model did not return a memo")
    return memo, result
