"use client";
import { fmt } from "@/lib/format";
import type { Doc, Fact, MemoNumber, Row, Verifier } from "@/lib/types";

const FUNCS = new Set(["min", "max", "abs", "round"]);

export default function SourceDrawer({ number, facts, rows, docs, verifier, onClose }: {
  number: MemoNumber | null; facts: Fact[]; rows: Row[]; docs: Doc[]; verifier: Verifier; onClose: () => void;
}) {
  if (!number) return null;
  const factById = new Map(facts.map((f) => [f.id, f]));
  const rowById = new Map(rows.map((r) => [r.id, r]));
  const docById = new Map(docs.map((d) => [d.id, d]));
  const ids = number.ref ? [number.ref]
    : Array.from(new Set((number.calc ?? "").match(/[A-Za-z_][A-Za-z0-9_]*/g) ?? [])).filter((x) => !FUNCS.has(x));
  const used = ids.map((id) => factById.get(id)).filter((f): f is Fact => !!f);
  const problem = verifier.blocked.find((b) => b.where === number.id);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/30" onClick={onClose}>
      <aside onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate">Where this number comes from</p>
            <p className="num mt-1 text-3xl font-semibold">{fmt(number)}</p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-slate hover:bg-ivory">Close</button>
        </div>

        {problem ? (
          <p className="mt-4 rounded-lg bg-red-soft p-3 text-sm text-red"><b>Blocked.</b> {problem.reason}</p>
        ) : (
          <p className="mt-4 rounded-lg bg-sage p-3 text-sm text-green"><b>Traced.</b> Recomputed from the records and it matches.</p>
        )}

        {number.calc && (
          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate">Formula</p>
            <p className="mt-1 break-words rounded-lg bg-ivory p-3 font-mono text-xs">{number.calc}</p>
          </div>
        )}

        {used.map((f) => {
          const src = f.rows.map((id) => rowById.get(id)).filter((r): r is Row => !!r);
          return (
            <section key={f.id} className="mt-6">
              <p className="text-sm font-semibold">{f.label}</p>
              <p className="num text-sm text-slate">{fmt(f)} · computed from {src.length ? `${src.length} statement lines` : "the loan terms"}</p>
              {src.length > 0 && (
                <ul className="mt-2 max-h-64 divide-y divide-line overflow-y-auto rounded-lg border border-line text-xs">
                  {src.slice(0, 40).map((r) => (
                    <li key={r.id} className="px-3 py-2">
                      <span className="font-mono text-slate">{docById.get(r.doc_id)?.name} · line {r.line + 1}</span>
                      <div className="num mt-0.5 font-mono">{docById.get(r.doc_id)?.lines[r.line]}</div>
                    </li>
                  ))}
                  {src.length > 40 && <li className="px-3 py-2 text-slate">and {src.length - 40} more lines</li>}
                </ul>
              )}
            </section>
          );
        })}
      </aside>
    </div>
  );
}
