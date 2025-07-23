# Overview – Daily Futures DQ Prototype
*Last updated: 2025‑07‑23*

## Purpose
A reproducible, config‑driven pipeline that ingests the daily‑futures CSV, runs automated data‑quality checks, flags & cleans anomalies, and outputs human‑readable + machine‑usable diagnostics.

## Core Goals
1. **Configurable validation** – rules & severities in `dq_config.yml`.
2. **Row‑level enrichment** – natural‑language explanations & severity tags for RAG.
3. **Notebook narrative** – EDA ➜ checks ➜ cleaning ➜ enrichment ➜ summary.
4. **CI‑tested repo** – black/flake8 + pytest + nbval on GitHub Actions.

## Success Metrics
* All 8 checks implemented; > 95 % of seeded anomalies flagged.
* `dq_report.csv` + `futures_with_flags.parquet` produced without errors.
* Row‑level explanations embedded & queryable in vector store demo.
* CI passes on a fresh clone / Codespace in < 5 min.

## Repository Layout
.
├── .cursor/
│   └── rules/
│       ├── memory.mdc        # always‑load memory bank
│       ├── plan.mdc          # rules for planning mode
│       └── implement.mdc     # implementation & debug rules
├── data/
│   ├── raw/                  # original futures_dataset.csv
│   └── processed/            # cleaned & flagged outputs
├── dq_config.yml             # severity & threshold config
├── docker-compose.yml        # spins up local Qdrant
├── notebooks/
│   ├── 00_exploration.ipynb
│   ├── 01_quality_checks.ipynb
│   ├── 02_cleaning.ipynb
│   ├── 03_summary.ipynb
│   └── 04_enrich.ipynb
├── src/
│   ├── __init__.py
│   ├── quality_checks.py     # validation functions
│   └── agent_enrich.py       # row-level LLM enrichment
├── memory_bank/
│   ├── overview.md
│   ├── plan.md
│   ├── product_context.md
│   ├── progress.md
│   ├── stack.md
│   └── system.md
├── tests/
│   └── test_quality_checks.py
├── requirements.txt
├── environment.yml
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
