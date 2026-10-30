"""Minimal API so the web app works today. Joel can mount his /analyze router here or replace this file."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import tf_client  # noqa: F401  (loads backend/.env)
from .demo_routes import has_key, router

app = FastAPI(title="Proof of Business")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True, "token_factory_key_set": has_key()}
