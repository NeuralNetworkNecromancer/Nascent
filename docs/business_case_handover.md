# Daily Futures Data Quality Prototype – Business Case & Engineer Handover

*Last updated: 2025-07-24*

> “Building confidence in synthetic market data through automation, transparency & AI-assisted context.”

---

## 1. Executive Summary
This repository contains a **production-style prototype** that tackles the Data Quality Analysis assignment for a daily futures dataset while also showcasing how AI tooling can accelerate root-cause analysis and stakeholder communication.  
The solution:
1. **Validates** the raw CSV against 14 configurable rules (schema, price sanity, liquidity, etc.).
2. **Surfaces** issues via an interactive **Streamlit** dashboard so analysts can slice, dice, and override.
3. **Enriches** flagged rows with GPT-generated explanations & trend tags to demonstrate automated escalation.
4. **Persists** embeddings in a lightweight **Chroma DB** for Retrieval-Augmented Chat (RAG).
5. Captures **all logic in Python modules**, tested CLI scripts, and Markdown docs so a new engineer can get productive within **30 minutes**.

## 2. System Architecture (High Level)
```mermaid
flowchart TD
    A[raw futures_dataset.csv] --> B[quality_checks.py]\nRules Registry
    B -->|flags| C(enriched_futures_data.csv)
    C --> D[Streamlit UI]\napp/main.py
    D --> E[User Actions]\nAdjust thresholds, export, chat
    C --> F[vector_db.py]\nChroma Embeddings
    subgraph GPT Enrichment
        C -.->|scripts/enrich_full_dataset.py| G[OpenAI API]
    end
```
Key touch points for an engineer:
* **`src/quality_checks.py`** – data-quality engine & rule registry.
* **`app/main.py`** – Streamlit dashboard orchestrating load → validate → AI chat.
* **`scripts/*`** – one-off CLI helpers for enrichment & merges (all idempotent).
* **`app/prompts/*.md`** – prompt templates for LLM calls; easy to iterate.
* **`memory_bank/*`** – context storage for agentic reasoning; see section 6.

## 3. Environment & Quick-Start
```bash
# 0. Clone & install deps
$ git clone <repo> && cd Nascent
$ pip install -r requirements.txt

# 1. Run quality checks as a one-shot CSV
$ python -m src.quality_checks futures_dataset.csv  # writes flags_*.csv

# 2. Launch interactive dashboard (with live reload)
$ streamlit run streamlit_app.py

# 3. Optional – generate GPT explanations (≈3-5 min, 3.5-turbo)
$ python scripts/enrich_full_dataset.py --model gpt-3.5-turbo
```
Secrets: export `OPENAI_API_KEY`.  All other parameters are CLI flags or UI sliders.

## 4. Mapping the Assignment ↔ Implementation
| Assignment Task | Where It’s Addressed | Engineer Notes |
|-----------------|----------------------|----------------|
| **1. Data Exploration** | `Streamlit › Data Preview` tab renders head/tail, descriptive stats and per-contract time-series plots via *Altair*. | For code-only workflows run `src.quality_checks.load_data()` and call `.describe()` / `plotly.express` helpers. |
| **2. Data Quality Assessment** | `src/quality_checks.py` implements 14 heuristics (see `docs/data_quality_checks.md`). UI colours by severity. | Rules are pure functions. Add/override by extending `CHECK_FUNCTIONS` dict. |
| **3. Documentation & Summary** | Current document + `docs/data_quality_checks.md`. Dashboard auto-generates a Markdown summary download. | Visuals embedded in Streamlit; export ⟶ PDF works out-of-the-box. |
| **4. Remediation Suggestions** | Each rule returns offending rows; CLI `scripts/calc_flags_full.py` creates a **flag file** so you can suppress / patch. | For gaps we **forward-fill** if gap ≤ 3 business days *and* `Volume = 0` (likely exchange outage). Longer gaps are left as *NaN* for downstream modelling. |

### Fill vs. Gap Heuristic
1. **Short Holiday Gap (≤3 days)** – forward-fill prices, set `Volume = 0`; rationale: holiday closure.
2. **Exchange Halt (flatline + high OI)** – back-populate with last good tick but mark as `halted` in metadata.
3. **Data Vendor Miss (>3 days)** – **do NOT fill**; instead raise `major` alert.  Rationale: risk of phantom pricing.
4. **End-of-Series Roll** – if contract disappears after expiry, treat as expected termination (minor notice).
Configuration lives in `app/utils/config.py` so ops can tweak without code deploy.

## 5. AI Usage Details
| Stage | LLM Prompt | File | Purpose |
|-------|------------|------|---------|
| Anomaly Explanation | “Explain *why* the following row is suspicious …” | `app/prompts/row_enrich.md` | Generates analyst-friendly text. |
| Trend Tagging | “Across these rows, identify common patterns …” | `app/prompts/trend_enrich.md` | Clusters related issues for dashboard filtering. |
| RAG Chat | Vector-store similarity search + `chat_rag.md` | `app/services/vector_db.py` | Lets users ask “Why are NG contracts flat in Feb?” and receive context-aware answers.* |

We deliberately kept chains **simple & transparent** (no unseen agents) so newcomers can debug every token.
*This prototype serves as demonstration only and likely needs some more time invest/better models to perform well (gpt-3.5 hallucinated quite a bit which can be mitigated in various ways: smarter model, reflection, ragas, context engineering, etc.).

## 6. Onboarding Checklist (≤30 min)
1. **Read** `docs/data_quality_checks.md` for rule primer.
2. **Run** the quick-start commands above; verify Streamlit loads.
3. **Explore** the “Config” sidebar – change a threshold, watch UI refresh.
4. **Generate** enrichment for 5 rows (`--sample 5`) to save tokens.
5. **Add** a toy rule (e.g., `unexpected_symbol`) and confirm it appears.
6. **Push** a PR – GitHub Actions runs `pytest` + lint.

## 7. FAQ
**Q: Where do I change severity mappings?**  
A: `src.quality_checks.DEFAULT_SEVERITIES` or via UI dropdown → *Save Config*.

**Q: How heavy is GPT usage?**  
A: ~1500 in-/out- tokens per anomaly. For full dataset (≈5 K rows) cost ≈ $2.50 using gpt-3.5-turbo.

**Q: Can we swap in AWS Bedrock or Azure OpenAI?**  
A: Yes – override `OpenAIBase` in `app/services/openai_service.py`.

**Q: How to schedule daily runs?**  
A: Use the provided GitHub Action template (`.github/workflows/qa.yml`) that triggers on new data, commits `enriched_*.csv` as artifact, and pings Slack via webhook.

## 8. Known Limitations / Next Steps
* **Statistical tests** (e.g., ARIMA residuals) could improve jump detection.
* **Vector index** enriching context before and after retrival.
* **Back-testing** pipeline not wired; ideal for verifying that QC improves PnL stability.
* **Unit coverage** aim for ≥90 % before prod.
* **Confidence checks** floating QCs rather than booleans indicating confidence level.
* **Drill** these quality checks can be expanded in so many ways and even drilling into them already provides much more insight.
* **Chat basics** the bot is more a gimmic than a functioning tool. 



## 9. Action Log Recap (for audit)
| # | Activity | Time | Rationale |
|---|----------|------|-----------|
|1|Prompted ChatGPT with raw email|1 min|Baseline, avoid bias|
|2|Exploratory reading on crypto context|20 min|Validate domain assumptions|
|3|AI-assisted scaffold in Cursor|60 min|Bootstrap codebase & rules|
|4|Refactor to Streamlit|30 min|Faster iteration than Jupyter|
|5|Build core app & AI hooks|4 h|End-to-end prototype|
|6|Loosing almost all code + recovery|30 min|It was late. I forgot to commit...|
|7|Clean, doc & deploy|30 min|Meet submission formatting|
|8|Draft this handover|30 min|Smooth onboarding|

---