export type Rec = "approve" | "approve_smaller" | "decline" | "need_more_info";

export type Row = { id: string; doc_id: string; line: number; date: string; amount: number;
  direction: "in" | "out"; counterparty: string; category: string };
export type Doc = { id: string; kind: string; name: string; lines: string[] };
export type Fact = { id: string; label: string; value: number; unit: string; rows: string[] };
export type MemoNumber = { id: string; value: number; unit: string; ref?: string | null; calc?: string | null };
export type Memo = { sections: { title: string; body: string }[]; numbers: MemoNumber[]; recommendation: Rec };
export type Verifier = { passed: number; total: number; blocked: { where: string; reason: string }[] };
export type TraceStep = { step: string; model: string; tokens_in: number; tokens_out: number; ms: number };

export type Ask = { amount: number | null; purpose: string; tenor_months: number | null };
export type Persona = { slug: string; name: string; business: string; location: string; story: string; ask: Ask };

export type Underwritten = {
  docs: Doc[]; rows: Row[]; facts: Fact[]; memo: Memo; verifier: Verifier; trace: TraceStep[];
  meta: Persona; mode: "live" | "offline";
  assumptions: { annual_rate: number; rate_is_placeholder: boolean; cover_target: number; stress_drop: number;
    stress_min_cover: number; min_months: number; ask: Ask };
};

export type AskResult = { answer: string; numbers: MemoNumber[]; verifier: Verifier; trace: TraceStep[]; mode: "live" | "offline" };
