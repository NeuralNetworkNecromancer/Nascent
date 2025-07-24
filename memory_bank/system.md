# System Patterns & Conventions

* **Layered repo:** app (Streamlit) → src utilities → scripts (batch) → data
* **DQ checks:** one pure function per rule in `src/quality_checks.py`; registry dict maps names ➜ funcs.
* **Severity config:** defaults in code; overridable in UI.
* **Enrichment flow (v1):** offline script populates AI columns, merge script ensures 1-to-many safe join.
* **Chat pane:** thin OpenAI wrapper with retry; GPT-4o; project key via `.env`.
* **CI/Pre-commit:** black, isort, pytest (pending).
