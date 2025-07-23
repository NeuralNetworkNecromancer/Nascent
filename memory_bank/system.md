# System Patterns & Conventions

* **Layered repo:** notebooks → src helpers → config → data
* **One rule = one function** in `quality_checks.py` (< 40 LOC each)
* **Severity enum:** critical = 0, major = 1, minor = 2 (from config)
* **Agent enrichment flow:** DataFrame ➜ JSON prompt ➜ LLM ➜ merged back
* **Commit hygiene:** nbstripout, black, isort before push
