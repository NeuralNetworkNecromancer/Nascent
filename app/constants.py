from __future__ import annotations

"""app/constants.py
Centralizes configuration constants for the application.
Loads environment variables (supports .env via python-dotenv).
"""
from os import getenv

# Auto-load environment variables from .env (root project dir) when running local scripts.
try:
    from dotenv import load_dotenv

    # Always override so that edits to .env are picked up in fresh runs
    load_dotenv(override=True)  # noqa: E402  # ignore if .env missing
except ModuleNotFoundError:
    # python-dotenv optional at runtime (already in requirements for dev)
    pass

# Load .env if present
load_dotenv()

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str | None = getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_EMBED_MODEL: str = getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

# ── ChromaDB ────────────────────────────────────────────────────────────────
CHROMA_PATH: str = getenv("CHROMA_PATH", ".chromadb")
