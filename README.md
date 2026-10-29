# Proof of Business

Lender-ready credit files for informal small businesses, built from the records they already have: mobile-money statements, receipt photos and WhatsApp orders. Every number in the credit file traces back to the line it came from.

Built for the Nebius x NVIDIA Global AI Hackathon (Best Apps & Agents track). License: MIT.

## How it uses NVIDIA Nemotron on Nebius Token Factory
| Step | Model | Why this size |
|---|---|---|
| Read receipts and screenshots | Nemotron vision (TBD) | Images to text |
| Extract every statement line | Nemotron 3 Nano | High volume, cheap, fast |
| Write the credit memo and size the loan | Nemotron 3 Ultra | Serious reasoning |
| Answer the loan officer's questions | Nemotron 3 Super | Fast and good enough |

A deterministic verifier checks every number Ultra writes against facts computed in Python. Untraced numbers are blocked.

## Setup
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # add your Token Factory key and model ids
.venv/bin/python -m pytest -q
cd .. && backend/.venv/bin/python scripts/check_models.py --list
```

_More to come: web app, deploy, demo video, feedback._
