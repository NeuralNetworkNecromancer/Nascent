"""scripts/enrich_full_dataset.py
Populate AI_Explanation and AI_Trend columns for EVERY row in the dataset using
GPT-3.5-turbo (cheaper & faster).

This can be long-running and costly; consider subsampling for tests.

Usage (defaults shown):

    python scripts/enrich_full_dataset.py \
        --input app/data/raw/futures_dataset.csv \
        --out   app/data/processed/enriched_full_by_ai.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys, pathlib

# Ensure project root on PYTHONPATH so 'app' package is importable when script run directly
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import pandas as pd
from tqdm import tqdm

from app.services import openai_service as oai

ROW_PROMPT = Path("app/prompts/row_enrich.md").read_text()
TREND_PROMPT = Path("app/prompts/trend_enrich.md").read_text()


def build_context(df_sym: pd.DataFrame, idx: int, window: int = 7) -> pd.DataFrame:
    """Return rows (as list[dict]) within *window* days up to current index (inclusive)."""
    current_date = df_sym.iloc[idx]["Date"]
    mask = (df_sym["Date"] >= current_date - window) & (df_sym["Date"] <= current_date)
    return df_sym.loc[mask]


def explain_row(row: pd.Series, context_rows: pd.DataFrame) -> tuple[str, str]:
    ctx_records = context_rows.to_dict(orient="records")
    row_dict = row.to_dict()
    prompt_explain = (
        ROW_PROMPT.replace("{{row}}", str(row_dict))
        .replace("{{checks}}", "auto")
        .replace("{{context}}", str(ctx_records))
    )

    prompt_trend = TREND_PROMPT.replace("{{context}}", str(ctx_records))

    explanation = oai.complete(prompt_explain, model="gpt-3.5-turbo")
    trend = oai.complete(prompt_trend, model="gpt-3.5-turbo")
    return explanation, trend


def main(input_path: Path, out_path: Path, batch_size: int = 100):
    df = pd.read_csv(input_path)
    df["Date"] = df["Date"].astype(int)
    explanations: list[str] = []
    trends: list[str] = []

    total_rows = len(df)
    pbar = tqdm(total=total_rows, desc="Enriching rows", unit="row")

    buffer_expl: list[str] = []
    buffer_trend: list[str] = []

    processed = 0
    for symbol, grp in df.groupby("Symbol"):
        grp_sorted = grp.sort_values("Date").reset_index()
        for idx, row in grp_sorted.iterrows():
            ctx = build_context(grp_sorted, idx)
            expl, tr = explain_row(row, ctx)
            buffer_expl.append(expl)
            buffer_trend.append(tr)
            processed += 1
            pbar.update(1)

            # Flush to master lists every batch_size rows to free memory
            if processed % batch_size == 0:
                explanations.extend(buffer_expl)
                trends.extend(buffer_trend)
                buffer_expl.clear()
                buffer_trend.clear()

    # append remaining buffers
    explanations.extend(buffer_expl)
    trends.extend(buffer_trend)

    pbar.close()

    df["AI_Explanation"] = explanations
    df["AI_Trend"] = trends

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved enriched dataset to {out_path} (rows: {len(df)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=Path("app/data/raw/futures_dataset.csv")
    )
    parser.add_argument(
        "--out", type=Path, default=Path("app/data/processed/enriched_full_by_ai.csv")
    )
    parser.add_argument(
        "--batch", type=int, default=100, help="Flush buffer every N rows"
    )
    args = parser.parse_args()

    main(args.input, args.out, args.batch)
