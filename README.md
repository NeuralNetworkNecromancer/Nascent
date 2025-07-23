# Nascent Daily Futures Data-Quality Prototype

This repository contains a reproducible, config-driven pipeline that ingests a daily futures CSV, runs automated data-quality checks, flags & cleans anomalies, and outputs human-readable + machine-usable diagnostics.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run Qdrant (optional for enrichment)
```bash
docker compose up -d qdrant
```

## Notebooks
| Notebook | Purpose |
|----------|---------|
| 00_exploration.ipynb | Explore schema, basic stats, visuals |
| 01_quality_checks.ipynb | Prototype & test validation logic |
| 02_cleaning.ipynb | Dedupe, fix, and flag anomalies |
| 03_summary.ipynb | Generate charts & summary metrics |
| 04_enrich.ipynb | LLM-based row-level enrichment |

## License
MIT 