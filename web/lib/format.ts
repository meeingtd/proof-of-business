import type { MemoNumber } from "./types";

export function fmt(n: Pick<MemoNumber, "value" | "unit">): string {
  const sign = n.value < 0 ? "-" : "";
  const v = Math.abs(n.value);
  const comma = (x: number, d = 0) => x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  if (n.unit === "GHS") return `${sign}GHS ${comma(v)}`;
  if (n.unit === "pct") return `${sign}${comma(v)}%`;
  if (n.unit === "ratio") return `${sign}${comma(v, 2)}x`;
  return `${sign}${Number.isInteger(v) ? comma(v) : comma(v, 2)}`;
}

export const REC_LABEL: Record<string, string> = {
  approve: "Approve as asked",
  approve_smaller: "Approve a smaller loan",
  decline: "Decline for now",
  need_more_info: "More information needed",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthName = (key: string) => MONTHS[parseInt(key.slice(5, 7), 10) - 1];
