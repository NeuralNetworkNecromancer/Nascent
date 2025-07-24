# Data-Quality Checks & AI Enrichment

*Last updated: 2025-07-24*

This document is the **single source of truth** for how our Daily Futures prototype validates raw data, how those alerts surface in the Streamlit dashboard, and how the optional GPT-powered enrichment works.

---

## 1. Library Overview

All validation logic lives in `src/quality_checks.py`.  Each rule is a **pure function** that accepts a `pd.DataFrame` and returns a *filtered* DataFrame of offending rows.  A registry (`CHECK_FUNCTIONS`) maps human-readable names → callables so the UI & batch scripts can enumerate checks dynamically.

### Public
| Function                     | Purpose                                          |
|------------------------------|--------------------------------------------------|
| `load_data(path=None)`       | Convenience CSV loader used by UI & CLI scripts. |
| `CHECK_FUNCTIONS`            | Name → rule callable mapping.                    |
| `DESCRIPTIONS`               | Name → plain-English description.                |
| `DEFAULT_SEVERITIES`         | Name → `critical` \| `major` \| `minor`.         |

All other helpers (flatline detection, schema dict, etc.) are considered **internal** but are exported for unit testing.

---

## 2. Rule Catalogue

| Rule                          | Description                                         | Default Severity | Key Parameters |
|-------------------------------|-----------------------------------------------------|------------------|------------------------------------|
| Duplicate row                 | Ensure each `(Date, Symbol)` appears only once.     | major            | –                                  |
| Missing date*                 | Find calendar gaps per symbol.                      | minor            | –                                  |
| OHLC range violation          | `High` < `Low` or Open/Close outside `[Low, High]`. | critical         | –                                  |
| Stagnant price                | Prices flat & `Volume = 0`.                         | major            | –                                  |
| Flat price anomaly            | Prices flat **and** `Volume ≥ min_volume`.          | minor            | `min_volume` (UI slider)           |
| Zero-volume with move         | Price changed but `Volume = 0`.                     | major            | derived from `volume_factor`       |
| Extreme volume outlier        | `Volume > N × median` for the symbol.               | minor            | `volume_factor` (UI slider)        |
| Day-over-day jump             | `|Close%Δ|` > *threshold*.                          | minor            | `pct_change_threshold` (UI slider) |
| Absolute price bounds *(IQR)* | Price outside `Q1-mult×IQR`→`Q3+mult×IQR`.          | minor            | `iqr_multiplier` (UI slider)       |
| High < Low inversion          | Explicit inversion check.                           | critical         | –                                  |
| Negative numeric              | Any negative price/volume/OI field.                 | critical         | –                                  |
| Schema                        | Column presence & dtype assertions.                 | critical         | governed by `EXPECTED_COLUMNS`     |
| Open interest                 | Negative OI or > `spike_factor × median`.           | minor            | `spike_factor` (hard-coded 10 ×)   |

*this is a check that was tested in the first draft and applied to 2 futures which lacked continuing data. Going forward I'd a minor alert indicating if a series is disscontinued.
---

## 3. Severity Policy

* **Critical (🔴)** – Data is definitely wrong and **must** be fixed before downstream use (e.g. `High < Low`).
* **Major (🟠)** – High likelihood of issue; manual confirmation advised (e.g. price change with zero volume).
* **Minor (🟢)** – Unusual but sometimes legitimate (e.g. stagnant prices on exchange holidays).

The dashboard lets users **re-map** severities at runtime; defaults are provided by `src.quality_checks.DEFAULT_SEVERITIES`.

---

## 4. Configurable Thresholds

Threshold sliders live in the sidebar (`app/main.py`) and store values in `st.session_state['dq_config']` via helpers in `app/utils/config.py`.

NOTE: Although not really meaningful it demonstrates how quality check tresholds and parameters can be abstracted for business/tech user GUI.
This in combination with the initial prompt for the task or the AI workflow under section 5. is to demonstrate how data quality checks show potential for pipeline automation through AI.

| Key                     | Default    | Usecase                                       |
|-------------------------|------------|-----------------------------------------------|
| `volume_factor`         | 10.0       | Extreme volume outlier, Volume multiplier     |
| `pct_change_threshold`  | 0.05       | Day-over-day jump ratio                       |
| `iqr_multiplier`        | 1.0        | IQR (inter-quartile ranges) multiple factor   |
| `flat_price_min_volume` | 1          | Flat price with volumes above treshold        |

---

## 5. AI Enrichment Workflow

> Optional — not required for running the dashboard.
NOTE: Also results aren't great yet due to limited infrastructure, ressources and time. There are a lot of low hanging fruits to optimize this pipeline.
This in combination with the initial prompt for the task or the config workflow under section 4. is to demonstrate how data quality checks show potential for pipeline automation through AI.

```
raw CSV ─▶ checks ─▶ flagged dataset
            │
            └─▶ scripts/enrich_full_dataset.py  (GPT-3.5 only for showcase now and cost/time efficient. Results aren't great)
                    │
                    ▼
          enriched_futures_data.csv  (adds AI_Explanation & AI_Trend)
```

1. Batch CLI script loads the base dataset and flagged rows.
2. Prompts in `app/prompts/*.md` ask GPT-3.5 to *explain* each anomaly and tag broader **trend** patterns.
3. Responses are merged back using `scripts/calc_flags_full.py` (ensures idempotency).
4. When the dashboard detects `AI_Explanation` columns, it shows them + enables RAG chat.

---

## 6. Extending / Adding a New Check

```python
# my_rules.py
from src.quality_checks import CHECK_FUNCTIONS, DESCRIPTIONS, DEFAULT_SEVERITIES

def unexpected_symbol(df):
    return df[~df["Symbol"].isin({"CL", "NG", "RB"})]

CHECK_FUNCTIONS["Unknown symbol"] = unexpected_symbol
DESCRIPTIONS["Unknown symbol"] = "Trades for symbols not in the allowed list."
DEFAULT_SEVERITIES["Unknown symbol"] = "critical"
```

Add an import in `app/main.py` **before** building the `param_wrappers` dict so the new rule appears in the multiselect list.

---

## 7. Deployment Notes

Streamlit Community Cloud looks for `streamlit_app.py` at the repo root.  That file simply imports `app.main`, ensuring the full UI is available.  Remember to:

1. Set the `OPENAI_API_KEY` in the *Secrets* section to enable chat & enrichment.
2. Schedule the GPT & enrichment scripts outside Streamlit (e.g. GitHub Action + Artifact) to avoid timeouts.

