"""Ask-the-file: a loan officer's follow-up question, answered by Nemotron Super under the same verifier.

Scenario questions ("what if sales fall 30%?") are answered with `calc` expressions over fact ids,
so the arithmetic is checked in Python, not trusted from the model.
"""
from __future__ import annotations

import json
import re
from typing import Callable, List, Optional, Tuple

from pydantic import BaseModel, ValidationError

from . import tf_client
from .memo import ChatFn, _extract_json, _facts_block
from .schemas import Fact, LoanAsk, Memo, MemoNumber, MemoSection, TraceStep, VerifierResult
from .verifier import verify

SYSTEM = """You answer a loan officer's follow-up question about one small business, using only the FACTS given, \
which were computed from its own mobile-money records.

HARD RULES
1. Never write a digit in the answer text. Every number, amount, percentage, count or duration must be a \
placeholder like [[n1]].
2. Each placeholder needs an entry in "numbers": {"id":"n1","value":<number>,"unit":"<GHS|pct|count|months|ratio>", \
and exactly one of "ref" (a fact id, value copied exactly) or "calc" (arithmetic over fact ids and constants \
using + - * / ( ) only)}.
3. For "what if" questions, build the answer from calc expressions over fact ids. Useful pieces: monthly stock cost is \
out_cat_stock_purchase / months_covered; costs other than stock are out_avg_month - out_cat_stock_purchase / months_covered. \
A sales fall of one third, for example, keeps two thirds of in_avg_month. The calc must give the value you state.
4. If the facts cannot answer the question, say so in plain words and use no numbers. Never guess.
5. Short, direct, at most five sentences.

Return ONLY JSON: {"answer":"...","numbers":[...]}"""

REPAIR = """Your answer failed verification. Fix ONLY these problems and return the complete JSON again:
{problems}"""


class AskReply(BaseModel):
    answer: str
    numbers: List[MemoNumber] = []


class AskResult(BaseModel):
    answer: str                  # contains [[nX]] placeholders
    numbers: List[MemoNumber]
    verifier: VerifierResult
    trace: List[TraceStep]


def _check(reply: AskReply, facts: List[Fact]) -> VerifierResult:
    shell = Memo(sections=[MemoSection(title="Answer", body=reply.answer)], numbers=reply.numbers,
                 recommendation="need_more_info")
    return verify(shell, facts)


def _parse(text: str) -> AskReply:
    try:
        return AskReply.model_validate(_extract_json(text))
    except (ValueError, ValidationError) as e:
        raise ValueError(f"reply was not valid: {str(e)[:300]}")


def ask_file(question: str, facts: List[Fact], ask: Optional[LoanAsk], context: str, trace: List[TraceStep],
             chat_fn: Optional[ChatFn] = None) -> AskResult:
    chat = chat_fn or tf_client.chat
    user = f"BUSINESS: {context}\n\nFACTS (id | label | value):\n{_facts_block(facts)}\n\nQUESTION: {question}"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    reply = chat("super", messages, step="ask", trace=trace, temperature=0.2, max_tokens=2500)

    parsed: Optional[AskReply] = None
    result: Optional[VerifierResult] = None
    for attempt in range(2):
        try:
            parsed = _parse(reply)
        except ValueError as e:
            problems = str(e)
        else:
            result = _check(parsed, facts)
            if result.ok:
                break
            problems = "\n".join(f"- {b.where}: {b.reason}" for b in result.blocked)
        if attempt == 0:
            messages = messages + [{"role": "assistant", "content": reply},
                                   {"role": "user", "content": REPAIR.format(problems=problems)}]
            reply = chat("super", messages, step="ask-repair", trace=trace, temperature=0.1, max_tokens=2500)
    if parsed is None or result is None:
        raise RuntimeError("model did not return a usable answer")
    return AskResult(answer=parsed.answer, numbers=parsed.numbers, verifier=result, trace=trace)


def make_offline_ask(facts: List[Fact], question: str) -> Callable[..., str]:
    """Offline sample only: recognises 'sales fall N%' and answers that one scenario from the facts."""
    f = {x.id: x.value for x in facts}

    def chat(role, messages, step, trace, **kw) -> str:
        from .offline import MODEL_NAME
        trace.append(TraceStep(step=step, model=MODEL_NAME))
        m = re.search(r"(\d{1,2})\s*(?:%|percent)", question)
        if not m or "out_cat_stock_purchase" not in f:
            return json.dumps({"answer": "This offline sample can only answer questions of the form 'what if "
                                         "sales fall by some percent'. The live model answers any question the "
                                         "records can support.", "numbers": []})
        pct = int(m.group(1))
        keep = 1 - pct / 100
        expr = (f"in_avg_month * {keep:g} - (out_cat_stock_purchase / months_covered * {keep:g} + "
                f"(out_avg_month - out_cat_stock_purchase / months_covered))")
        net = f["in_avg_month"] * keep - (f["out_cat_stock_purchase"] / f["months_covered"] * keep
                                          + (f["out_avg_month"] - f["out_cat_stock_purchase"] / f["months_covered"]))
        numbers = [{"id": "n1", "value": pct, "unit": "pct", "calc": str(pct)},
                   {"id": "n2", "value": round(net, 2), "unit": "GHS", "calc": expr}]
        text = "If sales fell by [[n1]], stock costs would fall with them and other costs would stay, leaving net cash flow of [[n2]] a month"
        if "instalment" in f:
            numbers.append({"id": "n3", "value": round(net / f["instalment"], 2), "unit": "ratio",
                            "calc": f"({expr}) / instalment"})
            text += ", which covers the instalment [[n3]]"
        return json.dumps({"answer": text + ".", "numbers": numbers})

    return chat
