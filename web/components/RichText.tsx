"use client";
import { fmt } from "@/lib/format";
import type { MemoNumber } from "@/lib/types";

/** Renders prose with [[nX]] placeholders as clickable number chips. Blocked numbers show in red. */
export default function RichText({ text, numbers, blocked, onPick }: {
  text: string; numbers: MemoNumber[]; blocked: Set<string>; onPick: (n: MemoNumber) => void;
}) {
  const byId = new Map(numbers.map((n) => [n.id, n]));
  const parts = text.split(/(\[\[n\d+\]\])/g);
  return (
    <>
      {parts.map((p, i) => {
        const m = p.match(/^\[\[(n\d+)\]\]$/);
        if (!m) return <span key={i}>{p}</span>;
        const n = byId.get(m[1]);
        if (!n) return <span key={i} className="text-red">[missing]</span>;
        const bad = blocked.has(n.id);
        return (
          <button key={i} onClick={() => onPick(n)} title={bad ? "Does not trace to the records" : "Click to see the source"}
            className={`num mx-0.5 rounded-md px-1.5 py-0.5 text-[0.95em] font-medium transition ${
              bad ? "bg-red-soft text-red ring-1 ring-red/40 hover:bg-red-soft/70"
                  : "bg-mist text-teal-dark hover:bg-teal hover:text-white"}`}>
            {fmt(n)}
          </button>
        );
      })}
    </>
  );
}
