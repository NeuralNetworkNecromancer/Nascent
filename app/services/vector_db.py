"""app/services/vector_db.py
Utility wrapper around ChromaDB for local vector store persistence.

This module exposes minimal helper functions that other parts of the app can
import without having to know any Chroma-specific APIs. Embeddings are generated
via the existing OpenAI service wrapper so we maintain a single place for retry
logic and authentication.
"""

from __future__ import annotations

import logging
from typing import List

# ---------------------------------------------------------------------------
# Ensure a modern SQLite (≥3.35) – required by Chroma. Streamlit Cloud ships
# with an older build, so we monkey-patch with pysqlite3-binary if necessary.
# ---------------------------------------------------------------------------

import sqlite3
from packaging import version

if version.parse(sqlite3.sqlite_version) < version.parse("3.35.0"):
    try:
        import pysqlite3  # type: ignore

        import sys

        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
        import sqlite3 as _patched  # noqa: F401 (ensures module initialised)
        logging.getLogger(__name__).info(
            "Patched sqlite3 with pysqlite3-binary (%s)", _patched.sqlite_version
        )
    except ImportError as _err:  # fall back to no-op handling later
        logging.getLogger(__name__).warning(
            "pysqlite3-binary not available (%s); Chroma may fail", _err
        )


try:
    import chromadb
    from chromadb.api.types import EmbeddingFunction  # type: ignore

    _CHROMA_AVAILABLE = True
except (ImportError, RuntimeError) as exc:  # RuntimeError for sqlite version
    # Log and fall back to no-op vector store.
    import warnings  # noqa: WPS433 (standard lib)

    warnings.warn(
        f"ChromaDB unavailable – vector search disabled. Reason: {exc}",
        RuntimeWarning,
    )
    chromadb = None  # type: ignore
    _CHROMA_AVAILABLE = False


from app.constants import CHROMA_PATH
from app.services.openai_service import embed

logger = logging.getLogger(__name__)


if _CHROMA_AVAILABLE:

    class OpenAIEmbeddingFunction(EmbeddingFunction):
        """EmbeddingFunction adapter that delegates to OpenAI embeddings."""

        def __call__(self, texts: List[str]) -> List[List[float]]:  # type: ignore[override]
            logger.debug("Generating %d embeddings via OpenAI", len(texts))
            return embed(texts)

else:
    # Dummy placeholder so type-checkers still find the symbol
    class OpenAIEmbeddingFunction:  # type: ignore
        pass


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------


if _CHROMA_AVAILABLE:

    def get_client() -> chromadb.PersistentClient:  # type: ignore
        """Return a (cached) persistent Chroma client bound to CHROMA_PATH."""
        return chromadb.PersistentClient(path=CHROMA_PATH)  # type: ignore


    def get_collection(name: str = "futures_rag"):  # type: ignore
        """Return a Chroma collection configured with OpenAI embeddings."""
        client = get_client()
        return client.get_or_create_collection(
            name=name,
            embedding_function=OpenAIEmbeddingFunction(),
        )

else:

    def get_client():  # type: ignore
        raise RuntimeError("ChromaDB not available in this environment.")


    def get_collection(name: str = "futures_rag"):  # type: ignore
        raise RuntimeError("ChromaDB not available; vector store disabled.")


# ---------------------------------------------------------------------------
# CRUD helpers (no-op fallbacks when Chroma is unavailable)
# ---------------------------------------------------------------------------


def add_documents(
    texts: List[str],
    metadatas: List[dict] | None = None,
    ids: List[str] | None = None,
    *,
    collection_name: str = "futures_rag",
) -> None:
    """Add documents with optional metadata/ids to the specified collection."""
    if not _CHROMA_AVAILABLE:
        logger.warning("ChromaDB unavailable – skipping add_documents call.")
        return

    collection = get_collection(collection_name)
    logger.info(
        "Adding %d documents to Chroma collection '%s'", len(texts), collection_name
    )
    collection.add(
        documents=texts,
        metadatas=metadatas or [{} for _ in texts],
        ids=ids
        or [str(i) for i in range(collection.count(), collection.count() + len(texts))],
    )


def query(
    texts: List[str],
    n_results: int = 5,
    *,
    collection_name: str = "futures_rag",
):
    """Query the vector store and return the matching documents and metadata."""
    if not _CHROMA_AVAILABLE:
        logger.warning("ChromaDB unavailable – returning empty query result.")
        return {}

    collection = get_collection(collection_name)
    return collection.query(query_texts=texts, n_results=n_results)


# ---------------------------------------------------------------------------
# CLI Entrypoint (optional)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Quick ad-hoc Chroma queries")
    parser.add_argument("--text", required=True, help="Query text")
    parser.add_argument(
        "--top", type=int, default=5, help="Number of results to return"
    )
    args = parser.parse_args()

    results = query([args.text], n_results=args.top)
    print("Results:", results)
