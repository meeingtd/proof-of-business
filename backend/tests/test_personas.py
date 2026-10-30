import json

import pytest

from app import personas
from app.facts import build_facts


@pytest.mark.parametrize("slug", list(personas.SPECS))
def test_rows_match_statement_lines(slug):
    docs, rows, ask, meta = personas.generate(slug)
    lines = docs[0].lines
    assert rows, "persona has no rows"
    for r in rows:
        date, direction, amount, cp, _ref = personas.parse_line(lines[r.line])
        assert (date, direction, amount, cp) == (r.date, r.direction, r.amount, r.counterparty)
        assert r.doc_id == docs[0].id
    assert len({r.id for r in rows}) == len(rows)
    assert len({r.line for r in rows}) == len(rows)


@pytest.mark.parametrize("slug", list(personas.SPECS))
def test_deterministic(slug, tmp_path):
    personas.write_all(tmp_path / "a")
    personas.write_all(tmp_path / "b")
    for name in ("docs.json", "rows.json", "ask.json", "meta.json"):
        assert (tmp_path / "a" / slug / name).read_text() == (tmp_path / "b" / slug / name).read_text()
    docs, rows, ask, _ = personas.load(slug, tmp_path / "a")
    assert [r.model_dump() for r in rows] == [r.model_dump() for r in personas.generate(slug)[1]]


def test_no_unmasked_names_or_phones():
    for slug in personas.SPECS:
        docs, _, _, _ = personas.generate(slug)
        text = "\n".join(docs[0].lines)
        assert "+233" not in text and "024" not in text and "@" not in text


def test_stories_show_up_in_the_numbers():
    f = {s: {x.id: x.value for x in build_facts(personas.generate(s)[1], personas.generate(s)[2])}
         for s in personas.SPECS}
    assert f["fish-seller"]["top_payer_share"] > 40      # concentrated on a restaurant
    assert f["fish-seller"]["months_negative"] >= 1      # the slow month
    assert f["provisions-shop"]["top_payer_share"] < 10  # diversified
    assert f["provisions-shop"]["months_negative"] == 0
    assert f["tailor"]["net_avg_month"] < f["fish-seller"]["net_avg_month"]
    assert all(v["months_covered"] == 6 for v in f.values())
