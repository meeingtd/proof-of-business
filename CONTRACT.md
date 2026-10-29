# Team contract: who builds what

Source of truth for the data shapes is `backend/app/schemas.py`. Change it only after you both agree.

## Pipeline
```
uploads ──► Doc[] ──► Row[] ──► Fact[] ──► Memo ──► VerifierResult ──► UI
           (Joel)    (Joel)     (done)    (Julian)    (done)          (Julian)
          parse+mask  Nano/VL   facts.py   Ultra      verifier.py
```

## Joel owns
- `POST /analyze` (multipart: files + business type + optional loan ask) → `AnalyzeResponse`
- Parsing PDF/CSV/images into `Doc.lines`, with phone numbers and names masked **before** any model call
- Extraction of `Row`s with **Nemotron Nano** (statement text) and the **vision model** (receipt/screenshot images). Every row keeps `doc_id` + `line` so the UI can show its source.
- Deploying the backend on Nebius Serverless Endpoint

## Julian owns
- `facts.py` (done) and `verifier.py` (done, 9 tests): Ultra may cite only facts; any number that doesn't trace is BLOCKED
- Memo generation with **Nemotron Ultra**, plus one repair pass if the verifier blocks
- Ask-the-file chat with **Nemotron Super**, the Tavily market check, the Next.js UI, the README, the video and the submission

## Shared rules
- Every model call goes through `tf_client.chat(role, ..., step=, trace=)` so it shows in the pipeline panel.
- Amounts are always positive GHS. `direction` is "in" or "out". Dates are YYYY-MM-DD.
- No real customer data in the repo. Real material lives in `data/real/` (git-ignored) with consent.
