"""scripts/build_vector_index.py
Build a local ChromaDB vector index from an enriched futures dataset.

Usage (CLI):
    python scripts/build_vector_index.py --csv app/data/processed/enriched_futures_data.csv --collection futures_rag

The script concatenates the `AI_Explanation` and `AI_Trend` columns to form the
text that will be embedded. The entire row (as a dict) is stored as metadata so
it can be surfaced later during retrieval-augmented generation (RAG).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd
from tqdm import tqdm

from app.services.vector_db import add_documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def chunked(iterable: List, size: int):
    """Yield successive `size`-sized chunks from *iterable*."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def build_index(
    csv_path: Path, collection_name: str = "futures_rag", batch_size: int = 100
):
    """Read *csv_path* and add its rows to the Chroma index.

    Parameters
    ----------
    csv_path: Path
        Path to the CSV containing the enriched dataset.
    collection_name: str
        Name of the Chroma collection to use (will be created if missing).
    batch_size: int
        Number of rows to embed and add per request to avoid rate limits.
    """
    logger.info("Loading CSV: %s", csv_path)
    df = pd.read_csv(csv_path)

    missing_cols = {c for c in ("AI_Explanation", "AI_Trend") if c not in df.columns}
    if missing_cols:
        raise ValueError(f"CSV missing expected columns: {', '.join(missing_cols)}")

    docs = (df["AI_Explanation"].fillna("") + " " + df["AI_Trend"].fillna("")).tolist()
    metadatas = df.to_dict("records")  # type: ignore[assignment]

    # Create deterministic IDs: Date_Symbol or fallback to row index.
    if {"Date", "Symbol"}.issubset(df.columns):
        ids = (df["Date"].astype(str) + "_" + df["Symbol"].astype(str)).tolist()
    else:
        ids = [str(i) for i in range(len(df))]

    logger.info(
        "Indexing %d documents into collection '%s' (batch %d)",
        len(docs),
        collection_name,
        batch_size,
    )

    for doc_batch, meta_batch, id_batch in tqdm(
        zip(
            chunked(docs, batch_size),
            chunked(metadatas, batch_size),
            chunked(ids, batch_size),
        )
    ):
        try:
            add_documents(
                doc_batch, meta_batch, id_batch, collection_name=collection_name
            )
        except Exception as exc:
            logger.error(
                "Failed to add batch starting with id %s: %s", id_batch[0], exc
            )

    logger.info("Index build completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build ChromaDB index from enriched dataset"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default="app/data/processed/enriched_futures_data.csv",
        help="Path to enriched CSV",
    )
    parser.add_argument(
        "--collection", default="futures_rag", help="Chroma collection name"
    )
    parser.add_argument(
        "--batch", type=int, default=100, help="Batch size for embedding requests"
    )
    args = parser.parse_args()

    build_index(args.csv, collection_name=args.collection, batch_size=args.batch)
