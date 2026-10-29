"""Every number in the memo must trace to a fact, or it is BLOCKED.

Rules:
1. Prose may not contain raw numbers. Numbers appear only as [[nX]] placeholders.
2. Each placeholder must exist in memo.numbers.
3. A number with `ref` must equal that fact's value (within tolerance).
4. A number with `calc` may use only fact ids, numeric constants, + - * / ( ),
   min, max, abs, round; it must evaluate to the stated value (within tolerance).
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List

from .schemas import Blocked, Fact, Memo, VerifierResult

PLACEHOLDER = re.compile(r"\[\[(n\d+)\]\]")
# A digit run in prose, ignoring ones inside placeholders. Ordinals and years are still flagged:
# the memo should cite them as facts or write them in words.
RAW_NUMBER = re.compile(r"(?<![\w\[])\d[\d,]*(?:\.\d+)?")
REL_TOL = 0.005   # 0.5%
ABS_TOL = 0.51    # rounding to whole cedis / whole percent

_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}


class CalcError(ValueError):
    pass


def safe_eval(expr: str, env: Dict[str, float]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"cannot parse: {e.msg}")

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise CalcError(f"unknown fact '{node.id}'")
            return env[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if b == 0:
                raise CalcError("division by zero")
            return a / b
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCS and not node.keywords):
            return float(_FUNCS[node.func.id](*[ev(a) for a in node.args]))
        raise CalcError(f"not allowed: {ast.dump(node)[:60]}")

    return ev(tree)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * abs(b))


def verify(memo: Memo, facts: List[Fact]) -> VerifierResult:
    env = {f.id: f.value for f in facts}
    numbers = {n.id: n for n in memo.numbers}
    blocked: List[Blocked] = []

    for s in memo.sections:
        stripped = PLACEHOLDER.sub(" ", s.body)
        for m in RAW_NUMBER.finditer(stripped):
            blocked.append(Blocked(where=s.title, reason=f"untagged number '{m.group(0)}' in prose"))
        for pid in PLACEHOLDER.findall(s.body):
            if pid not in numbers:
                blocked.append(Blocked(where=s.title, reason=f"placeholder [[{pid}]] has no number"))

    for n in memo.numbers:
        if bool(n.ref) == bool(n.calc):
            blocked.append(Blocked(where=n.id, reason="needs exactly one of ref or calc"))
            continue
        if n.ref:
            if n.ref not in env:
                blocked.append(Blocked(where=n.id, reason=f"unknown fact '{n.ref}'"))
            elif not _close(n.value, env[n.ref]):
                blocked.append(Blocked(where=n.id,
                                       reason=f"says {n.value:g} but {n.ref} = {env[n.ref]:g}"))
            continue
        try:
            got = safe_eval(n.calc, env)
        except CalcError as e:
            blocked.append(Blocked(where=n.id, reason=f"calc '{n.calc}': {e}"))
            continue
        if not _close(n.value, got):
            blocked.append(Blocked(where=n.id, reason=f"says {n.value:g} but {n.calc} = {got:g}"))

    total = len(memo.numbers)
    bad_ids = {b.where for b in blocked}
    passed = sum(1 for n in memo.numbers if n.id not in bad_ids)
    return VerifierResult(passed=passed, total=total, blocked=blocked)


def render(body: str, memo: Memo) -> str:
    """Replace placeholders with formatted values (UI does its own chips; this is for plain text)."""
    numbers = {n.id: n for n in memo.numbers}

    def fmt(m: "re.Match[str]") -> str:
        n = numbers.get(m.group(1))
        if not n:
            return m.group(0)
        if n.unit == "GHS":
            return f"GHS {n.value:,.0f}"
        if n.unit == "pct":
            return f"{n.value:.0f}%"
        return f"{n.value:,.2f}".rstrip("0").rstrip(".") + (f" {n.unit}" if n.unit not in ("count", "ratio") else "")

    return PLACEHOLDER.sub(fmt, body)
