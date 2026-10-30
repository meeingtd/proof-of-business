import type { TraceStep, Verifier } from "@/lib/types";

const LABEL: Record<string, string> = {
  extract: "Read statement lines", vision: "Read receipt photos", memo: "Write credit memo",
  repair: "Repair pass", ask: "Answer question", "ask-repair": "Repair pass",
};

export default function PipelinePanel({ trace, mode, verifier, tampered, onTamper, onRestore, canTamper }: {
  trace: TraceStep[]; mode: "live" | "offline"; verifier: Verifier; tampered: boolean;
  onTamper: () => void; onRestore: () => void; canTamper: boolean;
}) {
  const ok = verifier.blocked.length === 0;
  return (
    <div className="space-y-5">
      <section className={`rounded-2xl p-5 ${ok ? "bg-sage" : "bg-red-soft"}`}>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate">Verifier</p>
        <p className={`num mt-1 text-3xl font-semibold ${ok ? "text-green" : "text-red"}`}>{verifier.passed}/{verifier.total}</p>
        <p className="text-sm">{ok ? "numbers traced to the records" : `${verifier.blocked.length} blocked`}</p>
        {!ok && (
          <ul className="mt-3 space-y-1 text-sm text-red">
            {verifier.blocked.map((b, i) => <li key={i}><b>{b.where}:</b> {b.reason}</li>)}
          </ul>
        )}
        {canTamper && (
          <button onClick={tampered ? onRestore : onTamper}
            className={`mt-4 w-full rounded-lg px-3 py-2 text-sm font-medium ${tampered
              ? "bg-white text-ink ring-1 ring-line hover:bg-ivory" : "bg-white text-red ring-1 ring-red/30 hover:bg-red-soft"}`}>
            {tampered ? "Restore original" : "Try tampering with one number"}
          </button>
        )}
      </section>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-line">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate">Pipeline</p>
        {mode === "offline" && (
          <p className="mt-2 rounded-lg bg-ivory p-2 text-xs text-slate">Offline sample: no Nebius call was made.</p>
        )}
        <ol className="mt-3 space-y-3">
          {trace.length === 0 && <li className="text-sm text-slate">No model calls yet.</li>}
          {trace.map((t, i) => (
            <li key={i} className="border-l-2 border-teal pl-3">
              <p className="text-sm font-medium">{LABEL[t.step] ?? t.step}</p>
              <p className="break-all font-mono text-xs text-teal-dark">{t.model}</p>
              <p className="num text-xs text-slate">{t.tokens_in.toLocaleString()} in · {t.tokens_out.toLocaleString()} out · {t.ms.toLocaleString()} ms</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
