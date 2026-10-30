"use client";
import { useState } from "react";
import { askFile } from "@/lib/api";
import type { LoanInput } from "@/lib/api";
import type { AskResult, MemoNumber, Verifier } from "@/lib/types";
import RichText from "./RichText";

const EXAMPLES = ["What happens if sales drop 30%?", "How dependent is the business on its largest customer?"];

export default function AskBox({ slug, loan, onPick }: {
  slug: string; loan: LoanInput; onPick: (n: MemoNumber, v: Verifier) => void;
}) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<AskResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function go(question: string) {
    if (!question.trim()) return;
    setBusy(true); setErr("");
    try { setRes(await askFile(slug, question, loan)); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  const blocked = new Set(res?.verifier.blocked.map((b) => b.where) ?? []);
  return (
    <section className="rounded-2xl bg-white p-6 ring-1 ring-line">
      <h2 className="text-lg font-semibold">Ask the file</h2>
      <p className="text-sm text-slate">Answers use only this trader&apos;s records, and every number is checked the same way.</p>
      <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); go(q); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask a follow-up question"
          className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 outline-none focus:border-teal focus:ring-2 focus:ring-mist" />
        <button disabled={busy} className="rounded-lg bg-teal px-4 py-2 font-medium text-white hover:bg-teal-dark disabled:opacity-60">
          {busy ? "..." : "Ask"}</button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((x) => (
          <button key={x} onClick={() => { setQ(x); go(x); }}
            className="rounded-full bg-ivory px-3 py-1 text-xs text-slate hover:bg-mist hover:text-teal-dark">{x}</button>
        ))}
      </div>
      {err && <p className="mt-3 rounded-lg bg-red-soft p-3 text-sm text-red">{err}</p>}
      {res && (
        <div className="mt-4 rounded-xl bg-ivory p-4 leading-relaxed">
          <RichText text={res.answer} numbers={res.numbers} blocked={blocked} onPick={(n) => onPick(n, res.verifier)} />
          <p className="num mt-3 text-xs text-slate">{res.verifier.passed}/{res.verifier.total} numbers traced
            {res.trace[0] && <> · <span className="font-mono">{res.trace[0].model}</span></>}</p>
        </div>
      )}
    </section>
  );
}
