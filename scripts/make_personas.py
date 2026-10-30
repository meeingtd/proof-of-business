"""Write the three synthetic trader personas to data/personas/.

Usage (repo root): backend/.venv/bin/python scripts/make_personas.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import personas  # noqa: E402
from app.facts import build_facts  # noqa: E402

for slug in personas.write_all():
    docs, rows, ask, meta = personas.generate(slug)
    f = {x.id: x.value for x in build_facts(rows, ask)}
    print(f"{slug:16} rows={len(rows):3}  in/mo={f['in_avg_month']:8.0f}  net/mo={f['net_avg_month']:7.0f}  "
          f"top payer={f.get('top_payer_share', 0):4.0f}%  negative months={f['months_negative']:.0f}")
