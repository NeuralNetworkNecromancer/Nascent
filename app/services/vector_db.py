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

import chromadb
from chromadb.api.types import EmbeddingFunction

from app.constants import CHROMA_PATH
from app.services.openai_service import embed

logger = logging.getLogger(__name__)


class OpenAIEmbeddingFunction(EmbeddingFunction):
    """EmbeddingFunction adapter that delegates to OpenAI embeddings."""

    def __call__(self, texts: List[str]) -> List[List[float]]:  # type: ignore[override]
        logger.debug("Generating %d embeddings via OpenAI", len(texts))
        return embed(texts)


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------


def get_client() -> chromadb.PersistentClient:
    """Return a (cached) persistent Chroma client bound to CHROMA_PATH."""
    # We intentionally create a new client on every call – chromadb is lightweight
    # and manages its own connection pooling. If this becomes a bottleneck we can
    # add functools.lru_cache.
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection(name: str = "futures_rag") -> chromadb.Collection:
    """Return a Chroma collection configured with OpenAI embeddings."""
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        embedding_function=OpenAIEmbeddingFunction(),
    )


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def add_documents(
    texts: List[str],
    metadatas: List[dict] | None = None,
    ids: List[str] | None = None,
    *,
    collection_name: str = "futures_rag",
) -> None:
    """Add documents with optional metadata/ids to the specified collection."""
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
    logger.debug(
        "Querying Chroma with %d text(s) (top %d results)", len(texts), n_results
    )
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
