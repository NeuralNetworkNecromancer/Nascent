"""scripts/merge_enriched.py
Merge the OpenAI-enriched subset (flagged rows) with the full dataset to create
`full_enriched_dataset.csv`.

Usage (from project root):

    python scripts/merge_enriched.py \
        --base app/data/raw/futures_dataset.csv \
        --enriched app/data/processed/enriched_dataset.csv \
        --out app/data/processed/full_enriched_dataset.csv

If no arguments are provided, the defaults above are used.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

DEFAULT_BASE = Path("app/data/raw/futures_dataset.csv")
DEFAULT_ENRICHED = Path("app/data/processed/enriched_dataset.csv")
DEFAULT_OUT = Path("app/data/processed/full_enriched_dataset.csv")


def merge(base_path: Path, enriched_path: Path, out_path: Path) -> None:
    if not base_path.exists():
        raise FileNotFoundError(f"Base dataset not found: {base_path}")
    if not enriched_path.exists():
        raise FileNotFoundError(f"Enriched subset not found: {enriched_path}")

    base_df = pd.read_csv(base_path)
    enrich_df = pd.read_csv(enriched_path)

    # Align dtypes for join keys
    base_df["Date"] = base_df["Date"].astype(int)
    enrich_df["Date"] = enrich_df["Date"].astype(int)

    # Collapse duplicates into a single row per (Date, Symbol)
    if enrich_df.duplicated(subset=["Date", "Symbol"]).any():
        text_cols = [
            c for c in ["AI_Explanation", "AI_Trend"] if c in enrich_df.columns
        ]
        agg: dict[str, str] = {
            col: "last" for col in enrich_df.columns if col not in ["Date", "Symbol"]
        }
        for col in text_cols:
            agg[col] = lambda s: " | ".join(s.dropna().unique())

        enrich_df = (
            enrich_df.sort_values(["Date", "Symbol"])  # deterministic
            .groupby(["Date", "Symbol"], as_index=False)
            .agg(agg)
        )

    enrich_cols = [c for c in enrich_df.columns if c not in base_df.columns]
    key_cols = ["Date", "Symbol"]

    merged = base_df.merge(
        enrich_df[key_cols + enrich_cols],
        on=key_cols,
        how="left",
        validate="one_to_one",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"Full enriched dataset saved to {out_path} (rows: {len(merged)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge enriched subset with full dataset."
    )
    parser.add_argument(
        "--base", type=Path, default=DEFAULT_BASE, help="Path to full base dataset CSV"
    )
    parser.add_argument(
        "--enriched",
        type=Path,
        default=DEFAULT_ENRICHED,
        help="Path to enriched subset CSV",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output CSV path")
    args = parser.parse_args()

    merge(args.base, args.enriched, args.out)
