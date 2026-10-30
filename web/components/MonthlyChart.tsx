import { fmt, monthName } from "@/lib/format";
import type { Fact } from "@/lib/types";

export default function MonthlyChart({ facts }: { facts: Fact[] }) {
  const f = new Map(facts.map((x) => [x.id, x.value]));
  const months = Array.from(new Set(facts.map((x) => x.id.match(/^in_(\d{4}_\d{2})$/)?.[1]).filter(Boolean) as string[])).sort();
  if (!months.length) return null;
  const data = months.map((m) => ({ m: m.replace("_", "-"), i: f.get(`in_${m}`) ?? 0, o: f.get(`out_${m}`) ?? 0 }));
  const max = Math.max(...data.flatMap((d) => [d.i, d.o])) * 1.1;
  const W = 560, H = 210, base = 160, bw = 26, gap = (W - data.length * bw * 2) / (data.length + 1);
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Money in and out by month">
        {data.map((d, k) => {
          const x = gap + k * (bw * 2 + gap), hi = (d.i / max) * 130, ho = (d.o / max) * 130, neg = d.i - d.o < 0;
          return (
            <g key={d.m}>
              <rect x={x} y={base - hi} width={bw} height={hi} rx={3} fill="#397F78"><title>Money in {fmt({ value: d.i, unit: "GHS" })}</title></rect>
              <rect x={x + bw} y={base - ho} width={bw} height={ho} rx={3} fill="#9AA6B4"><title>Money out {fmt({ value: d.o, unit: "GHS" })}</title></rect>
              <text x={x + bw} y={base + 18} textAnchor="middle" fontSize="12" fill="#687789">{monthName(d.m)}</text>
              {neg && <text x={x + bw} y={base + 34} textAnchor="middle" fontSize="11" fill="#B65F5A">net loss</text>}
            </g>
          );
        })}
        <line x1="0" x2={W} y1={base} y2={base} stroke="#E4E2D8" />
      </svg>
      <figcaption className="mt-1 flex gap-4 text-xs text-slate">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-teal" />Money in</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-[#9AA6B4]" />Money out</span>
      </figcaption>
    </figure>
  );
}
