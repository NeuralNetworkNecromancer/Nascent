"""scripts/calc_flags_full.py
Recompute all quality-check flags and severity aggregates for a CSV (e.g. enriched_full_by_ai.csv).
Adds boolean flag columns per check plus critical_flags / major_flags / minor_flags counts.
Saves output with *_with_flags.csv suffix or path passed by --out.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys, pathlib

# ensure project root on path
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pandas as pd
from src import quality_checks as qc


def compute_flags(df: pd.DataFrame) -> pd.DataFrame:
    # Map of check name -> boolean mask
    flag_cols: dict[str, pd.Series] = {}

    for name, func in qc.CHECK_FUNCTIONS.items():
        try:
            flagged_idx = func(df).index  # type: ignore
        except Exception:
            flagged_idx = pd.Index([])
        flag_cols[name] = df.index.isin(flagged_idx)

    flags_df = pd.DataFrame(flag_cols, index=df.index)

    # aggregate per severity
    for sev in ["critical", "major", "minor"]:
        checks_sev = [n for n, s in qc.DEFAULT_SEVERITIES.items() if s == sev and n in flags_df.columns]
        flags_df[f"{sev}_flags"] = flags_df[checks_sev].sum(axis=1).astype(int)

    return pd.concat([df, flags_df], axis=1)


def main(inp: Path, out: Path | None):
    df = pd.read_csv(inp)
    df["Date"] = df["Date"].astype(int)

    result = compute_flags(df)

    if out is None:
        out = inp.with_name(inp.stem + "_with_flags.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    print(f"Saved flagged dataset to {out} (rows {len(result)})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("app/data/processed/enriched_full_by_ai.csv"))
    p.add_argument("--out", type=Path, default=None, help="Output CSV path")
    args = p.parse_args()

    main(args.input, args.out) 