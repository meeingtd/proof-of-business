import type { AskResult, Fact, Memo, Persona, Underwritten, Verifier } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8010";

async function call<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json();
}

export type LoanInput = { amount: number; tenor_months: number; annual_rate: number };

export const listPersonas = () => call<Persona[]>("/demo/personas");
export const underwrite = (slug: string, loan: LoanInput) => call<Underwritten>(`/demo/${slug}/underwrite`, loan);
export const verifyMemo = (memo: Memo, facts: Fact[]) => call<Verifier>("/verify", { memo, facts });
export const askFile = (slug: string, question: string, loan: LoanInput) =>
  call<AskResult>(`/demo/${slug}/ask`, { question, ...loan });
