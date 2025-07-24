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
   • Dashboard auto-loads `enriched_futures_dataset.csv` and displays `AI_Explanation` & `AI_Trend`.
6. Removed obsolete notebook pages and Chat page; added slim chat pane in dashboard.
7. Documentation refresh across memory_bank: overview, stack, system docs markdowns.
8. Added local ChromaDB vector store, indexing script, and retrieval-augmented chat with contextual examples & similarity scoring.
9. **Refactor:** Removed legacy `eda_utils.py`, merged into `src/quality_checks.py`, unified severity config, updated caching & README, added `docs/data_quality_checks.md`.

## In-Progress / Next
* CI pipeline & tests for `quality_checks` rules.
* Local vector-store setup with ChromaDB for RAG indexing (P6).
* Optional RAG vector index (stretch).
* Finalize: codebase cleanup, documentation polish & Streamlit Cloud deployment

## Known Issues
* Enrichment script is single-threaded – runtime ~ N×80 s; consider async batch.
* Streamlit chat uses GPT-4o by default; can be slow without caching.
