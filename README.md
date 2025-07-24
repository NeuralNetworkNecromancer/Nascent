# Daily Futures – Data-Quality Dashboard  🚀

Interactive Streamlit prototype that **automates data-quality checks** for end-of-day futures data, enriches anomalies with GPT-3.5 explanations, and makes the results explorable via a single-page dashboard.

---

## Quick-start

```bash
# 1. Install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run streamlit_app.py

# (Optional)  GPT enrichment & vector index
export OPENAI_API_KEY="sk-…"
python scripts/enrich_full_dataset.py  # adds AI_Explanation column
```

---

## Documentation

• Full rule catalogue & architecture: [`docs/data_quality_checks.md`](docs/data_quality_checks.md)

---

## Repo Layout (key parts)

| Path | Purpose |
|------|---------|
| `app/` | Streamlit UI, prompts, OpenAI wrapper, config helpers |
| `src/quality_checks.py` | Core validation library (pure pandas) |
| `scripts/` | Batch utilities: GPT enrichment, merging, flag calc |
| `memory_bank/` | Planning & progress docs (internal) |
| `docs/` | Project & API documentation |

---

## Deployment to Streamlit Community Cloud
1. Push repo to GitHub.
2. Create new app ➜ pick `streamlit_app.py`.
3. Add `OPENAI_API_KEY` secret (optional for chat/enrichment).
4. Hit *Deploy* 🚀.

---

## License

MIT. 