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
├── app/
│   ├── __init__.py
│   ├── main.py                # Streamlit landing page (home)
│   ├── pages/                 # Multi-page reports
│   │   ├── 1_Coverage_and_Duplicates.py
│   │   ├── 2_OHLC_Integrity.py
│   │   ├── 3_Flatlines_and_Stale.py
│   │   └── 4_Outliers_and_Volume.py
│   └── data/                    # small demo CSVs for Cloud (optional)
│       ├── raw/                 # original futures_dataset.csv
│       └──processed/            # cleaned & flagged outputs
├── src/
│   ├── __init__.py
│   ├── eda_utils.py           # reusable diagnostics
│   ├── quality_checks.py      # rule implementations (TBD)
│   └── agent_enrich.py        # row-level LLM enrichment (stub)
├── tests/
│   └── test_quality_checks.py
├── data/
│   └── raw/futures_dataset.csv   # full dataset (git-large-file or ignored in Cloud)
├── dq_config.yml              # severity & threshold config
├── docker-compose.yml         # local Qdrant service
├── requirements.txt           # Python deps for app & src
├── .pre-commit-config.yaml    # formatting hooks
├── .gitignore
├── README.md
├── memory_bank/ …             # context & progress docs
├── .cursor/
│   └── rules/ (memory.mdc, plan.mdc, implement.mdc)
└── streamlit_app.py           # thin launcher (imports app.main)
