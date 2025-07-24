# Overview – Daily Futures DQ Prototype
*Last updated: 2025-07-24*

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

## Repository Layout (actual)
.
├── app/
│   ├── __init__.py
│   ├── main.py                  # single-page Streamlit dashboard
│   ├── constants.py             # env-var helpers (OpenAI keys)
│   ├── prompts/
│   │   ├── row_enrich.md        # LLM prompt templates
│   │   └── trend_enrich.md
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── caching.py           # st.cache wrapper
│   │   └── config.py            # default slider values (currently minimal)
│   ├── services/
│   │   ├── __init__.py
│   │   └── openai_service.py    # retry-wrapped OpenAI client
│   └── data/
│       ├── raw/                 # futures_dataset.csv (ignored in git)
│       └── processed/
│           ├── enriched_dataset.csv
│           └── 1full_enriched_dataset.csv
├── scripts/
│   ├── merge_enriched.py        # join base + AI subset safely
│   └── enrich_full_dataset.py   # batch GPT-3.5 enrichment CLI
├── src/
│   ├── __init__.py
│   └── quality_checks.py        # all data-quality rules & descriptions
├── requirements.txt             # pandas, streamlit, openai, python-dotenv, tqdm…
├── memory_bank/                 # plan / progress / stack / system docs (this folder)
├── README.md                    # high-level intro
├── .gitignore, .cursor/, .github/ …
└── streamlit_app.py             # thin launcher (imports app.main)
