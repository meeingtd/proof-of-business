"""Synthetic but realistic trader personas (deterministic, seeded). No real people or brands.

Each persona is a generic mobile-money statement (one Doc) plus ground-truth Rows that point
back to exact statement lines, so source chips in the UI can show the line a number came from.
"""
from __future__ import annotations

import json
import random
from calendar import monthrange
from pathlib import Path
from typing import Dict, List, Tuple

from .schemas import Doc, LoanAsk, Row

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "personas"
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]

# Each persona carries a story so the credit file has something to say.
SPECS: Dict[str, dict] = {
    "fish-seller": {
        "name": "Abena",
        "business": "Fresh and smoked fish seller",
        "location": "Cape Coast market",
        "story": "Two restaurants buy about half of everything. July is a slow month and she "
                 "restocks heavily before it, so cash flow dips below zero.",
        "seed": 11,
        "sales": {"count": [34, 30, 12, 24, 38, 42], "lo": 40, "hi": 160},
        "pool": 14, "top_share": 0.46,
        "stock_ratio": [0.55, 0.57, 1.75, 0.58, 0.54, 0.55],
        "stock_label": "Stock purchase - fish",
        "transport": 45, "personal": [2, 250],
        "ask": {"amount": 2800, "purpose": "Stock for the busy season", "tenor_months": 6},
    },
    "provisions-shop": {
        "name": "Kofi",
        "business": "Neighbourhood provisions shop",
        "location": "Cape Coast",
        "story": "Steady daily sales from many small customers, no dependence on any one buyer. "
                 "Wholesale restocking is the main cost.",
        "seed": 23,
        "sales": {"count": [88, 92, 90, 98, 100, 106], "lo": 8, "hi": 110},
        "pool": 60, "top_share": 0.05,
        "stock_ratio": [0.61, 0.60, 0.62, 0.60, 0.59, 0.60],
        "stock_label": "Stock purchase - wholesale",
        "transport": 60, "personal": [2, 250],
        "ask": {"amount": 4000, "purpose": "A second fridge and extra stock", "tenor_months": 6},
    },
    "tailor": {
        "name": "Ama",
        "business": "Tailor and school uniform maker",
        "location": "Cape Coast",
        "story": "Income is lumpy: a few large uniform orders drive most of the year, and "
                 "personal withdrawals are high relative to what the business earns.",
        "seed": 37,
        "sales": {"count": [12, 10, 9, 22, 26, 13], "lo": 40, "hi": 220},
        "pool": 9, "top_share": 0.30,
        "stock_ratio": [0.42, 0.45, 0.40, 0.50, 0.52, 0.44],
        "stock_label": "Fabric and thread",
        "transport": 70, "personal": [3, 350],
        "ask": {"amount": 9000, "purpose": "Two industrial sewing machines", "tenor_months": 6},
    },
}

HEADER_1 = "Mobile money statement | account holder [masked] | 2026-05-01 to 2026-10-31 | GHS"
HEADER_2 = "date | direction | amount | counterparty | reference"


def _money(x: float) -> float:
    return round(round(x / 5) * 5, 2) or 5.0


def _line(date: str, direction: str, amount: float, counterparty: str, ref: str) -> str:
    return f"{date} | {direction.upper()} | {amount:.2f} | {counterparty} | {ref}"


def parse_line(line: str) -> Tuple[str, str, float, str, str]:
    d, direction, amount, cp, ref = [p.strip() for p in line.split("|")]
    return d, direction.lower(), float(amount), cp, ref


def generate(slug: str) -> Tuple[List[Doc], List[Row], LoanAsk, dict]:
    spec = SPECS[slug]
    rng = random.Random(spec["seed"])
    customers = [f"Customer {chr(65 + i // 10)}{i % 10 + 1}" for i in range(spec["pool"])]
    top = customers[0]
    txs: List[Tuple[str, str, float, str, str, str]] = []  # date, dir, amt, cp, category, ref

    for mi, month in enumerate(MONTHS):
        y, m = int(month[:4]), int(month[5:])
        last = min(28, monthrange(y, m)[1])
        month_in = 0.0
        for _ in range(spec["sales"]["count"][mi]):
            day = rng.randint(1, last)
            cp = top if rng.random() < spec["top_share"] else rng.choice(customers[1:])
            # the biggest buyer pays in larger amounts
            hi = spec["sales"]["hi"] * (1.7 if cp == top and spec["top_share"] > 0.2 else 1)
            amt = _money(rng.uniform(spec["sales"]["lo"], hi))
            month_in += amt
            txs.append((f"{month}-{day:02d}", "in", amt, cp, "sales", "Payment received"))

        stock_total = month_in * spec["stock_ratio"][mi]
        n_stock = 3
        for k in range(n_stock):
            day = min(last, 3 + k * 9 + rng.randint(0, 3))
            amt = _money(stock_total / n_stock * rng.uniform(0.9, 1.1))
            txs.append((f"{month}-{day:02d}", "out", amt, f"Supplier S{k + 1}", "stock purchase",
                        spec["stock_label"]))
        for _ in range(4):
            txs.append((f"{month}-{rng.randint(1, last):02d}", "out",
                        _money(spec["transport"] * rng.uniform(0.6, 1.4)), "Transport", "transport",
                        "Transport"))
        n_personal, p_amt = spec["personal"]
        for _ in range(n_personal):
            txs.append((f"{month}-{rng.randint(1, last):02d}", "out",
                        _money(p_amt * rng.uniform(0.7, 1.3)), "Own account", "personal",
                        "Personal transfer"))

    txs.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    lines = [HEADER_1, HEADER_2]
    rows: List[Row] = []
    for i, (date, direction, amt, cp, cat, ref) in enumerate(txs):
        lines.append(_line(date, direction, amt, cp, ref))
        rows.append(Row(id=f"r{i + 1}", doc_id="d1", line=len(lines) - 1, date=date, amount=amt,
                        direction=direction, counterparty=cp, category=cat))
    docs = [Doc(id="d1", kind="statement", name=f"{slug}-statement.csv", lines=lines)]
    meta = {k: spec[k] for k in ("name", "business", "location", "story")}
    meta["slug"] = slug
    return docs, rows, LoanAsk(**spec["ask"]), meta


def write_all(out_dir: Path = DATA_DIR) -> List[str]:
    done = []
    for slug in SPECS:
        docs, rows, ask, meta = generate(slug)
        d = out_dir / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "docs.json").write_text(json.dumps([x.model_dump() for x in docs], indent=1))
        (d / "rows.json").write_text(json.dumps([x.model_dump() for x in rows], indent=1))
        (d / "ask.json").write_text(json.dumps(ask.model_dump(), indent=1))
        (d / "meta.json").write_text(json.dumps(meta, indent=1))
        done.append(slug)
    return done


def load(slug: str, base: Path = DATA_DIR) -> Tuple[List[Doc], List[Row], LoanAsk, dict]:
    d = base / slug
    docs = [Doc(**x) for x in json.loads((d / "docs.json").read_text())]
    rows = [Row(**x) for x in json.loads((d / "rows.json").read_text())]
    ask = LoanAsk(**json.loads((d / "ask.json").read_text()))
    return docs, rows, ask, json.loads((d / "meta.json").read_text())
