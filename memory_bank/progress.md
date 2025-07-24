# Progress & Known Issues  (Updated 2025-07-24)

## Completed
1. Repo scaffold, virtual-env, pre-commit hooks.
2. Replaced Jupyter notebooks with single-page Streamlit dashboard (`app/main.py`) including:
   • Config sliders, severity mapping, KPI metrics.
   • Interactive plots (daily metric, severity stacks, symbol bars).
   • Flagged-rows table with download buttons.
3. Centralised all data-quality rules in `src/quality_checks.py`; added new checks (schema, OI, flat-price split, etc.).
4. Added OpenAI service wrapper (`app/services/openai_service.py`) with retry + batch helpers.
5. Implemented offline AI enrichment:
   • `scripts/enrich_full_dataset.py` (GPT-3.5, progress bar, batching).
   • `scripts/merge_enriched.py` for safe merge/dedup.
   • Dashboard auto-loads `1full_enriched_dataset.csv` and displays `AI_Explanation` & `AI_Trend`.
6. Removed obsolete notebook pages and Chat page; added slim chat pane in dashboard.

## In-Progress / Next
* Documentation refresh (overview, stack, system docs).
* CI pipeline & tests for `quality_checks` rules.
* Optional RAG vector index (stretch).

## Known Issues
* Enrichment script is single-threaded – runtime ~ N×40 s; consider async batch.
* Streamlit chat uses GPT-4o by default; can be slow without caching.
