"""Hour-0 check: list NVIDIA models on Token Factory and ping the ones set in backend/.env.

Usage (from repo root):
  backend/.venv/bin/python scripts/check_models.py --list   # show NVIDIA/Nemotron model ids
  backend/.venv/bin/python scripts/check_models.py          # ping MODEL_NANO/SUPER/ULTRA/VISION
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import tf_client  # noqa: E402


def main() -> int:
    c = tf_client.client()
    if "--list" in sys.argv:
        ids = sorted(m.id for m in c.models.list().data)
        hits = [i for i in ids if "nemotron" in i.lower() or "nvidia" in i.lower()]
        print(f"{len(ids)} models on Token Factory; NVIDIA/Nemotron ones:")
        for i in hits:
            print("  ", i)
        return 0

    failed = 0
    for role in tf_client.ROLES:
        try:
            trace = []
            out = tf_client.chat(role, [{"role": "user", "content": "Reply with the single word: ready"}],
                                 step="ping", trace=trace, max_tokens=200)
            t = trace[0]
            print(f"OK   {role:6} {t.model}  {t.ms} ms  in={t.tokens_in} out={t.tokens_out}  -> {out.strip()[:40]!r}")
        except Exception as e:  # report and keep going
            failed += 1
            print(f"FAIL {role:6} {type(e).__name__}: {str(e)[:160]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
