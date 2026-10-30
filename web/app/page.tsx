"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import AskBox from "@/components/AskBox";
import MonthlyChart from "@/components/MonthlyChart";
import PipelinePanel from "@/components/PipelinePanel";
import RichText from "@/components/RichText";
import SourceDrawer from "@/components/SourceDrawer";
import TraderPanel, { type Loan } from "@/components/TraderPanel";
import { listPersonas, underwrite, verifyMemo } from "@/lib/api";
import { fmt, REC_LABEL } from "@/lib/format";
import type { Memo, MemoNumber, Persona, Underwritten, Verifier } from "@/lib/types";

const REC_STYLE: Record<string, string> = {
  approve: "bg-sage text-green", approve_smaller: "bg-[#F3EBDD] text-[#8A6B2E]",
  decline: "bg-red-soft text-red", need_more_info: "bg-mist text-teal-dark",
};

export default function Home() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [slug, setSlug] = useState("");
  const [loan, setLoan] = useState<Loan>({ amount: 0, tenor_months: 6, ratePct: 30 });
  const [data, setData] = useState<Underwritten | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [picked, setPicked] = useState<{ n: MemoNumber; v: Verifier } | null>(null);
  const [tamper, setTamper] = useState<{ memo: Memo; verifier: Verifier } | null>(null);

  const build = useCallback(async (s: string, l: Loan) => {
    setBusy(true); setErr(""); setTamper(null);
    try {
      setData(await underwrite(s, { amount: l.amount, tenor_months: l.tenor_months, annual_rate: l.ratePct / 100 }));
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    listPersonas().then((ps) => {
      setPersonas(ps);
      const first = ps[0];
      if (!first) return;
      const l = { amount: first.ask.amount ?? 0, tenor_months: first.ask.tenor_months ?? 6, ratePct: 30 };
      setSlug(first.slug); setLoan(l); build(first.slug, l);
    }).catch(() => setErr("Cannot reach the API. Start it with: uvicorn app.main:app --port 8010"));
  }, [build]);

  function select(s: string) {
    const p = personas.find((x) => x.slug === s);
    if (!p) return;
    const l = { amount: p.ask.amount ?? 0, tenor_months: p.ask.tenor_months ?? 6, ratePct: loan.ratePct };
    setSlug(s); setLoan(l); build(s, l);
  }

  async function doTamper() {
    if (!data) return;
    const idx = data.memo.numbers.findIndex((n) => n.unit === "GHS" && n.ref);
    if (idx < 0) return;
    const numbers = data.memo.numbers.map((n, i) => (i === idx ? { ...n, value: Math.round(n.value * 1.25) } : n));
    const memo = { ...data.memo, numbers };
    setTamper({ memo, verifier: await verifyMemo(memo, data.facts) });
  }

  const memo = tamper?.memo ?? data?.memo;
  const verifier = tamper?.verifier ?? data?.verifier;
  const blocked = useMemo(() => new Set(verifier?.blocked.map((b) => b.where) ?? []), [verifier]);
  const f = useMemo(() => new Map(data?.facts.map((x) => [x.id, x]) ?? []), [data]);
  const tile = (id: string, label: string) => {
    const x = f.get(id);
    return x ? (
      <div className="rounded-xl bg-white p-4 ring-1 ring-line" key={id}>
        <p className="text-xs text-slate">{label}</p>
        <p className="num mt-1 text-xl font-semibold">{fmt(x)}</p>
      </div>
    ) : null;
  };

  return (
    <main className="mx-auto max-w-[1400px] px-4 py-8 sm:px-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Proof of Business</h1>
          <p className="text-slate">Lender-ready credit files for small traders, with every number traced to the records.</p>
        </div>
        {data && (
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${data.mode === "live" ? "bg-mist text-teal-dark" : "bg-[#F3EBDD] text-[#8A6B2E]"}`}>
            {data.mode === "live" ? "Live: Nebius Token Factory + NVIDIA Nemotron" : "Offline sample: no model call"}
          </span>
        )}
      </header>

      {err && <p className="mb-6 rounded-xl bg-red-soft p-4 text-sm text-red">{err}</p>}

      <div className="grid gap-8 lg:grid-cols-[300px_minmax(0,1fr)_320px]">
        <aside><TraderPanel personas={personas} selected={slug} onSelect={select} loan={loan} setLoan={setLoan}
          onBuild={() => build(slug, loan)} busy={busy} /></aside>

        <section className={`space-y-6 ${busy ? "opacity-60" : ""}`}>
          {!data && !err && <p className="text-slate">Loading...</p>}
          {data && memo && (
            <>
              <div className={`rounded-2xl p-6 ${REC_STYLE[memo.recommendation]}`}>
                <p className="text-xs font-semibold uppercase tracking-wide opacity-80">Recommendation</p>
                <p className="mt-1 text-2xl font-semibold">{REC_LABEL[memo.recommendation]}</p>
                <p className="mt-1 text-sm opacity-90">
                  {data.meta.name} · {data.meta.business} · decided by the lender&apos;s rules
                  ({data.assumptions.cover_target}x cover, tested against a {Math.round(data.assumptions.stress_drop * 100)}% sales fall); the model explains it.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                {tile("in_avg_month", "Money in / month")}
                {tile("net_avg_month", "Net cash / month")}
                {tile("cover", "Repayment cover")}
                {tile("stress_cover", "Cover if sales fall 20%")}
                {tile("max_amount", "Largest loan that fits")}
              </div>

              <div className="rounded-2xl bg-white p-6 ring-1 ring-line">
                <h2 className="mb-2 text-lg font-semibold">Money in and out</h2>
                <MonthlyChart facts={data.facts} />
              </div>

              <article className="space-y-6 rounded-2xl bg-white p-6 ring-1 ring-line sm:p-8">
                {tamper && <p className="rounded-lg bg-red-soft p-3 text-sm text-red">One number in this file was edited. Click it to see why the check fails.</p>}
                {memo.sections.map((s) => (
                  <div key={s.title}>
                    <h2 className="text-lg font-semibold">{s.title}</h2>
                    <p className="mt-1 leading-relaxed">
                      <RichText text={s.body} numbers={memo.numbers} blocked={blocked}
                        onPick={(n) => setPicked({ n, v: verifier! })} />
                    </p>
                  </div>
                ))}
                <p className="border-t border-line pt-4 text-xs text-slate">
                  Click any highlighted number to see the statement lines it was computed from. Interest rate
                  ({Math.round(data.assumptions.annual_rate * 100)}% flat per year) is a placeholder assumption.
                </p>
              </article>

              <AskBox slug={slug} loan={{ amount: loan.amount, tenor_months: loan.tenor_months, annual_rate: loan.ratePct / 100 }}
                onPick={(n, v) => setPicked({ n, v })} />
            </>
          )}
        </section>

        <aside>
          {data && verifier && (
            <PipelinePanel trace={data.trace} mode={data.mode} verifier={verifier} tampered={!!tamper}
              canTamper={data.memo.numbers.some((n) => n.unit === "GHS" && n.ref)}
              onTamper={doTamper} onRestore={() => setTamper(null)} />
          )}
        </aside>
      </div>

      {data && <SourceDrawer number={picked?.n ?? null} verifier={picked?.v ?? data.verifier} facts={data.facts}
        rows={data.rows} docs={data.docs} onClose={() => setPicked(null)} />}
    </main>
  );
}
