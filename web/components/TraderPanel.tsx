"use client";
import type { Persona } from "@/lib/types";

export type Loan = { amount: number; tenor_months: number; ratePct: number };

export default function TraderPanel({ personas, selected, onSelect, loan, setLoan, onBuild, busy }: {
  personas: Persona[]; selected: string; onSelect: (slug: string) => void;
  loan: Loan; setLoan: (l: Loan) => void; onBuild: () => void; busy: boolean;
}) {
  const field = "num mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-base outline-none focus:border-teal focus:ring-2 focus:ring-mist";
  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate">1. Choose a trader</p>
        <div className="mt-3 space-y-3">
          {personas.map((p) => (
            <button key={p.slug} onClick={() => onSelect(p.slug)}
              className={`w-full rounded-2xl p-4 text-left ring-1 transition ${selected === p.slug
                ? "bg-mist ring-teal" : "bg-white ring-line hover:ring-slate/40"}`}>
              <p className="font-semibold">{p.name} <span className="font-normal text-slate">· {p.business}</span></p>
              <p className="text-xs text-slate">{p.location}</p>
              {selected === p.slug && <p className="mt-2 text-sm">{p.story}</p>}
            </button>
          ))}
        </div>
      </section>

      <section>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate">2. The loan being asked for</p>
        <label className="mt-3 block text-sm">Amount (GHS)
          <input className={field} type="number" min={0} step={100} value={loan.amount}
            onChange={(e) => setLoan({ ...loan, amount: Number(e.target.value) })} /></label>
        <label className="mt-3 block text-sm">Term (months)
          <input className={field} type="number" min={1} max={36} value={loan.tenor_months}
            onChange={(e) => setLoan({ ...loan, tenor_months: Number(e.target.value) })} /></label>
        <label className="mt-3 block text-sm">Flat interest per year (%)
          <input className={field} type="number" min={0} max={200} value={loan.ratePct}
            onChange={(e) => setLoan({ ...loan, ratePct: Number(e.target.value) })} /></label>
        <p className="mt-1 text-xs text-slate">Default is the midpoint of rates microfinance banks reported. The lender sets the real one.</p>
      </section>

      <button onClick={onBuild} disabled={busy}
        className="w-full rounded-xl bg-teal px-4 py-3 font-semibold text-white transition hover:bg-teal-dark disabled:opacity-60">
        {busy ? "Building credit file..." : "Build credit file"}
      </button>
    </div>
  );
}
