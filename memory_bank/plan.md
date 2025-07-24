# Plan (Master Task Checklist)

- [x] **P1-Scaffold:** repo folders, env files, config, Cursor rules
- [x] **P2-Dash:** Streamlit dashboard (`app/main.py`) with all checks, plots, downloads
- [x] **P3-Checks:** Refactored ALL rules into `src/quality_checks.py`; default severities/config in code
- [x] **P4-Cleaning:** flag join logic + cleaned view in dashboard
- [x] **P5-Enrichment (v1):** row-level OpenAI explanations via offline script (`scripts/enrich_full_dataset.py`) and integrated view
- [ ] **P6-Enrichment (v2):** automated trend detection & vector-store indexing (stretch)
- [ ] **P7-Docs & CI:** update README + markdown docs, add pytest/black pre-commit
- [ ] **P8-Deploy:** optional Streamlit Community Cloud manifest & Dockerfile
