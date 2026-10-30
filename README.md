# Proof of Business

Lender-ready credit files for informal small businesses, built from the records they already have, with **every number traced to the line it came from**.

Built for the Nebius x NVIDIA Global AI Hackathon, Best Apps & Agents track. License: MIT.

## The problem
Ghana's central bank says it plainly: a mobile money record "is a credit record", yet "we have not yet built equally extraordinary credit rails" (Matilda Asante-Asiedu, Bank of Ghana, 18 Aug 2026). A reported $4.8 billion annual SME financing gap sits in that gap. Traders have months of transaction history and no audited accounts, so lenders either pay for field visits or say no. See [research/ghana-facts.md](research/ghana-facts.md) for exact quotes and sources.

## What it does
A trader's statement goes in. A one-page credit file comes out: cash flow, customer concentration, personal withdrawals, repayment capacity, a stress test, risks and a recommendation. Click any number and see the statement lines it was computed from.

Two rules make it trustworthy:
1. **The model never does the arithmetic or makes the decision.** Python computes every figure ([facts.py](backend/app/facts.py), [underwriting.py](backend/app/underwriting.py)) and applies the lender's rule: approve at 1.5x repayment cover if cover also stays at or above 1.0x after sales fall 20%; approve smaller between 1.0x and 1.5x; decline below.
2. **A deterministic verifier blocks anything untraced** ([verifier.py](backend/app/verifier.py)). Nemotron may only write numbers as placeholders tied to a computed fact or an arithmetic expression over facts. If a number does not match, it is blocked, the model gets one repair attempt, and anything still wrong stays visibly flagged. Edit one figure in the demo and the check fails with the exact reason.

## How it uses NVIDIA Nemotron on Nebius Token Factory
| Step | Model role | Why this size | Code |
|---|---|---|---|
| Write the credit memo | Nemotron Ultra | Serious reasoning, plus the repair pass | [memo.py](backend/app/memo.py) |
| Answer the loan officer's questions | Nemotron Super | Fast, and still checked by the verifier | [ask.py](backend/app/ask.py) |
| Extract transactions from statements | Nemotron Nano | High volume, low cost | ingestion (in progress) |
| Read receipt and chat photos | Nemotron vision | Images to text | ingestion (in progress) |

Every model call goes through [tf_client.py](backend/app/tf_client.py), which records the model, tokens and latency of each step. The web app shows that list as the pipeline panel.

## Status (honest)
- Built and tested: synthetic traders, the underwriting rule, the memo step with repair, ask-the-file, the verifier, the API and the web app. 52 backend tests pass.
- **Not yet verified live:** calls to Token Factory. Until `NEBIUS_API_KEY` and the model IDs are set, the API returns an **offline sample** written by a fixed template, labelled "Offline sample: no model call" in the UI and the trace. It is never a Nemotron call.
- Not yet built: statement and receipt ingestion with Nano and vision, the cryptographic proof layer, Nebius deployment, the Tavily market check.
- The three traders (Abena, Kofi, Ama) are **synthetic**. No real people or mobile money brands.

## Run it
```bash
# API (port 8010)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env        # add NEBIUS_API_KEY and the MODEL_* ids to go live
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:app --port 8010

# Web app (port 3000), in a second terminal
cd web && npm install && npm run dev
```
Open http://localhost:3000. To check your key and model IDs: `backend/.venv/bin/python scripts/check_models.py --list`, then without `--list`.

## Repo map
- `backend/app/` : schemas, facts, underwriting rule, verifier, memo, ask, personas, API
- `backend/tests/` : verifier, rule branches, memo and ask with a fake model, API
- `web/` : Next.js app (credit file, source drawer, pipeline panel, tamper demo)
- `research/` : sourced facts for the pitch
- `CONTRACT.md` : who builds which part; `FEEDBACK.md` : running log of platform feedback
