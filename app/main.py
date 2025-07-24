"""Unified Data-Quality Dashboard – upload, configure, analyse, download."""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
# 'os' may still be used elsewhere; keep. Removed dotenv and openai import above.

from app.utils.caching import load_data
from app.utils.config import get_config, set_config, DEFAULT_SEVERITIES
from src import quality_checks as eu
from app.services.vector_db import query as rag_query
from pathlib import Path

DESCRIPTIONS = eu.DESCRIPTIONS
CHECK_FUNCTIONS = eu.CHECK_FUNCTIONS

TEMPLATE_CHAT = Path("app/prompts/chat_rag.md").read_text()

st.set_page_config(page_title="Daily Futures – DQ Dashboard", layout="wide")

# -----------------------------------------------------------------------------
# Sidebar – Upload & Config
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("1️⃣ Load dataset")
    uploaded = st.file_uploader("CSV with columns Date, Symbol, Open, High, Low, Close, Volume, Open Interest", type="csv")
    if uploaded is not None:
        st.session_state["data"] = load_data(uploaded)
        st.success("Dataset uploaded.")
    else:
        # attempt default load once
        if "data" not in st.session_state:
            from pathlib import Path as _P
            import pandas as _pd

            candidates = [
                _P("app/data/processed/enriched_futures_data.csv"),
                _P("app/data/processed/1full_enriched_dataset.csv"),
            ]
            found = next((p for p in candidates if p.exists()), None)
            if found is not None:
                st.session_state["data"] = _pd.read_csv(found)
                st.info(f"Loaded enriched dataset ({found.name}).")
            else:
                try:
                    st.session_state["data"] = load_data()
                    st.info("Loaded default dataset.")
                except FileNotFoundError:
                    st.warning("No default dataset found – please upload a CSV.")

    # Fetch dataset
    df = st.session_state["data"]
    # No additional filters – operate on full dataset
    df_view = df.copy()
    total_rows_filtered = len(df_view)

    if total_rows_filtered == 0:
        st.warning("No data loaded.")
        st.stop()

    st.divider()
    st.header("2️⃣ Plot dimension")

    dim_options = ["Open", "High", "Low", "Close", "Volume", "Open Interest"]
    plot_dimension = st.selectbox("Select field for plot", dim_options, index=dim_options.index("Volume"))

    st.divider()
    st.header("3️⃣ Configuration")
    cfg = get_config()
    # --- Volume factor slider with extended range and safe default ---
    vol_options = [10, 20, 50, 100, 1000]
    cfg_vol = int(cfg.get("volume_factor", 10))
    if cfg_vol not in vol_options:
        vol_options.append(cfg_vol)
        vol_options = sorted(vol_options)

    vol_factor = st.select_slider(
        "Extreme volume factor (× median)",
        options=vol_options,
        value=cfg_vol if cfg_vol in vol_options else vol_options[0],
        help="Flags rows where Volume exceeds this multiple of the symbol's median volume.",
    )

    pct_option = st.select_slider(
        "Day-over-day % price change threshold",
        options=[5, 10, 20, 30, 50],
        value=int(cfg.get("pct_change_threshold", 0.5) * 100),
        help="Flags rows where Close price changes more than this percentage from the previous day.",
    )
    pct_thresh = pct_option / 100

    iqr_mult = st.select_slider(
        "Price outlier range (IQR ×)",
        options=[1.0, 1.5, 2.0, 3.0],
        value=float(cfg.get("iqr_multiplier", 3.0)),
        help="Flags prices that sit well outside the normal range: more than this many IQRs (inter-quartile ranges) from typical prices.",
    )

    flat_min_vol = st.select_slider(
        "Flat price: min volume for anomaly",
        options=[1, 100, 10000],
        value=int(cfg.get("flat_price_min_volume", 1)),
        help="Rows with flat prices AND Volume ≥ this value are flagged as anomalies.",
    )

    set_config(
        volume_factor=vol_factor,
        pct_change_threshold=pct_thresh,
        iqr_multiplier=iqr_mult,
        flat_price_min_volume=flat_min_vol,
    )

    # ---------- Severity settings ----------
    st.divider()
    st.header("4️⃣ Severity mapping")
    if "severity_map" not in st.session_state:
        st.session_state["severity_map"] = DEFAULT_SEVERITIES.copy()

    sev_opts = ["critical", "major", "minor"]
    for check, default_sev in DEFAULT_SEVERITIES.items():
        sel = st.selectbox(check, sev_opts, index=sev_opts.index(st.session_state["severity_map"].get(check, default_sev)))
        st.session_state["severity_map"][check] = sel

# -----------------------------------------------------------------------------
# Main – Overview & Analytics
# -----------------------------------------------------------------------------

df: pd.DataFrame | None = st.session_state.get("data")
if df is None or df.empty:
    st.stop()

symbols_all = sorted(df["Symbol"].unique().tolist())

# ----- (Second sidebar filter section removed; df_view remains full dataset) -----

# Combine masks replaced lines already handled.

total_rows_filtered = len(df_view)

if total_rows_filtered == 0:
    st.warning("No data for selected filters.")
    st.stop()

st.title("📊 Data-Quality Analytics")

# Quick overview
descriptions = DESCRIPTIONS

severity_map = st.session_state["severity_map"]

emoji_map = {"critical": "🔴", "major": "🟠", "minor": "🟢"}

total_counts: dict[str, int] = {}
severity_masks = {"critical": pd.Series(False, index=df_view.index),
                  "major": pd.Series(False, index=df_view.index),
                  "minor": pd.Series(False, index=df_view.index)}

# Build parameter-aware wrappers matching earlier config
param_wrappers = {
    "Duplicate row": CHECK_FUNCTIONS["Duplicate row"],
    "Missing date": CHECK_FUNCTIONS["Missing date"],
    "OHLC range violation": CHECK_FUNCTIONS["OHLC range violation"],
    "Stagnant price": CHECK_FUNCTIONS["Stagnant price"],
    "Flat price anomaly": lambda d: eu.flat_price_anomaly(d, min_volume=flat_min_vol),
    "Zero-volume with move": lambda d: eu.volume_anomalies(d, factor=vol_factor)[0],
    "Extreme volume outlier": lambda d: eu.volume_anomalies(d, factor=vol_factor)[1],
    "Day-over-day jump": lambda d: eu.pct_change_outliers(d, threshold=pct_thresh),
    "Absolute price bounds (IQR)": lambda d: eu.iqr_price_outliers(d, multiplier=iqr_mult),
    "High < Low inversion": CHECK_FUNCTIONS["High < Low inversion"],
    "Negative numeric": CHECK_FUNCTIONS["Negative numeric"],
    "Schema": CHECK_FUNCTIONS["Schema"],
    "Open interest": CHECK_FUNCTIONS["Open interest"],
}

for name, func in param_wrappers.items():
    idx = func(df_view).index
    sev = severity_map[name]
    severity_masks[sev].loc[idx] = True
    total_counts[name] = len(idx)

with st.expander("Quality checks overview", expanded=False):
    for sev_key in ["critical", "major", "minor"]:
        names = sorted([name for name, s in severity_map.items() if s == sev_key])
        for k in names:
            v = descriptions[k]
            count = total_counts.get(k, 0)
            st.markdown(f"{emoji_map[sev_key]} **{k}** – {v} (_{sev_key}_, {count:,} rows)")

# --------- Select checks to run ---------
selected = st.multiselect("Select quality checks to run", list(param_wrappers.keys()), default=list(param_wrappers.keys()))

# Compute boolean columns for selected checks
flag_columns = {}
check_counts = {}
for name in selected:
    res = param_wrappers[name](df_view)
    idx = res.index if not res.empty else pd.Index([])
    mask = df_view.index.isin(idx)
    flag_columns[name] = mask
    check_counts[name] = len(idx)

# Build initial flags DataFrame
flags_df = pd.DataFrame(flag_columns, index=df_view.index)

# Add per-severity flag count columns
for sev in ["critical", "major", "minor"]:
    checks_sev = [n for n in selected if severity_map[n] == sev]
    if checks_sev:
        flags_df[f"{sev}_flags"] = flags_df[checks_sev].sum(axis=1).astype(int)
    else:
        # no checks of this severity selected – add column of zeros
        flags_df[f"{sev}_flags"] = 0

# DataFrame combining original view and flag info
df_flags = pd.concat([df_view, flags_df], axis=1)

union_mask = flags_df.any(axis=1)
# If AI-enriched dataset loaded, just display full dataset
if "AI_Explanation" in df_view.columns:
    flagged_rows = df_view.copy().reset_index(drop=True)
else:
    flagged_rows = df_flags[union_mask].reset_index(drop=True)

# Prepare cleaned dataset (rows WITHOUT any flagged alerts)
cleaned_df = df_view.loc[~union_mask].reset_index(drop=True)

# ------------ Plot -------------

# Build plotting df and ensure flag columns unique
df_plot = df_view.copy()
df_plot["Date_dt"] = pd.to_datetime(df_plot["Date"].astype(str), format="%Y%m%d", errors="coerce")

# Add flag columns if not already present (avoid duplicate join error)
cols_flags = ["critical_flags", "major_flags", "minor_flags"]
missing_cols = [c for c in cols_flags if c not in df_plot.columns]
if missing_cols:
    df_plot = df_plot.join(df_flags[missing_cols])

# Helper to classify highest severity for plotting
def _sev_level(row):
    if row["critical_flags"] > 0:
        return "critical"
    if row["major_flags"] > 0:
        return "major"
    if row["minor_flags"] > 0:
        return "minor"
    return "none"

df_plot["sev_level"] = df_plot.apply(_sev_level, axis=1)

sev_colors = {"critical": "#d62728", "major": "#ff7f0e", "minor": "#2ca02c", "none": "#1f77b4"}

agg_df = df_plot.groupby(["Date_dt", "sev_level"], as_index=False)[plot_dimension].mean()

chart = (
    alt.Chart(agg_df)
    .mark_bar()
    .encode(
        x=alt.X("Date_dt:T", title="Date"),
        y=alt.Y(f"{plot_dimension}:Q", title=plot_dimension),
        color=alt.Color(
            "sev_level:N",
            scale=alt.Scale(domain=list(sev_colors.keys()), range=list(sev_colors.values())),
            legend=None,
        ),
        tooltip=["Date_dt:T", plot_dimension, "sev_level"],
    )
    .properties(height=300)
)

# Stacked bar: count of rows per severity per day (for selected checks)

count_df = (
    df_flags.loc[:, ["Date"] + [f"{s}_flags" for s in ["critical", "major", "minor"]]]
    .assign(Date_dt=lambda d: pd.to_datetime(d["Date"].astype(str), format="%Y%m%d", errors="coerce"))
    .melt(id_vars="Date_dt", value_vars=["critical_flags", "major_flags", "minor_flags"],
          var_name="sev", value_name="flag")
    .query("flag > 0")
    .replace({"sev": {"critical_flags": "critical", "major_flags": "major", "minor_flags": "minor"}})
    .groupby(["Date_dt", "sev"], as_index=False)["flag"].size()
    .rename(columns={"size": "rows"})
)

stack_chart = (
    alt.Chart(count_df)
    .mark_bar()
    .encode(
        x="Date_dt:T",
        y="rows:Q",
        color=alt.Color("sev:N", scale=alt.Scale(domain=list(sev_colors), range=list(sev_colors.values())), legend=None),
        tooltip=["Date_dt:T", "sev", "rows"]
    )
    .properties(height=220)
)

# ---------------- Symbol-level severity chart ----------------

# Compute counts of alerts per severity for each symbol
symbol_count_df = (
    df_flags.loc[:, ["Symbol"] + [f"{s}_flags" for s in ["critical", "major", "minor"]]]
    .melt(id_vars="Symbol", value_vars=["critical_flags", "major_flags", "minor_flags"],
          var_name="sev", value_name="flag")
    .query("flag > 0")
    .replace({"sev": {"critical_flags": "critical", "major_flags": "major", "minor_flags": "minor"}})
    .groupby(["Symbol", "sev"], as_index=False)["flag"].size()
    .rename(columns={"size": "rows"})
)

# Stacked bar per Symbol coloured by severity
sym_chart = (
    alt.Chart(symbol_count_df)
    .mark_bar()
    .encode(
        x=alt.X("Symbol:N", title="Symbol", sort="-y"),
        y=alt.Y("rows:Q", title="# Alerts"),
        color=alt.Color(
            "sev:N",
            scale=alt.Scale(domain=list(sev_colors.keys()), range=list(sev_colors.values())),
            legend=None,
        ),
        tooltip=["Symbol", "sev", "rows"],
    )
    .properties(height=220)
)

# ---------------- Layout: dashboard vs chat -----------------

dash_col, chat_col = st.columns([4, 1], gap="large")

# ----- Left: Dashboard -----
with dash_col:
    # Severity KPIs
    st.subheader("Severity flag counts (selected checks)")
    crit, maj, minr = st.columns(3)
    crit.metric("🔴 Critical", f"{int(flags_df['critical_flags'].sum()):,}")
    maj.metric("🟠 Major", f"{int(flags_df['major_flags'].sum()):,}")
    minr.metric("🟢 Minor", f"{int(flags_df['minor_flags'].sum()):,}")

    # Charts
    with st.expander("📈 Visualisations", expanded=True):
        st.altair_chart(chart, use_container_width=True)
        st.altair_chart(stack_chart, use_container_width=True)
        st.altair_chart(sym_chart, use_container_width=True)

    # Flagged rows table & downloads
    with st.expander("Flagged rows", expanded=False):
        if flagged_rows.empty:
            st.success("No rows failed the selected checks 🎉")
        else:
            st.subheader("Flagged rows")
            st.write(f"Rows flagged: {len(flagged_rows):,}")
            _df = flagged_rows.copy()
            for col in ["AI_Explanation","AI_Trend"]:
                if col not in _df.columns:
                    _df[col] = ""
            ordered = [c for c in _df.columns if c not in ("AI_Explanation","AI_Trend")] + ["AI_Explanation","AI_Trend"]
            st.dataframe(_df[ordered])

            csv_flagged_rows = flagged_rows.to_csv(index=False).encode("utf-8")
            csv_full_flags = df_flags.to_csv(index=False).encode("utf-8")
            csv_cleaned = cleaned_df.to_csv(index=False).encode("utf-8")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button("📥 Full data + flags", csv_full_flags, "full_data_with_flags.csv", "text/csv")
            with col2:
                st.download_button("🧹 Cleaned data", csv_cleaned, "cleaned_data.csv", "text/csv")
            with col3:
                st.download_button("💾 Flagged rows", csv_flagged_rows, "flagged_rows.csv", "text/csv")

    # Per-check metrics
    st.subheader("Counts per selected check")
    cols_metrics = st.columns(min(4, len(selected)))
    for i, name in enumerate(selected):
        cols_metrics[i % len(cols_metrics)].metric(label=name, value=f"{check_counts[name]:,}")

# ----- Right: Chat -----
with chat_col:
    st.markdown("### 🤖 Chat")

    # Inform if no API key
    from app.constants import OPENAI_API_KEY
    if not OPENAI_API_KEY:
        st.info("Set OPENAI_API_KEY in .env to enable chatbot.")

    import app.services.openai_service as oai

    if "chat_msgs" not in st.session_state:
        st.session_state.chat_msgs = [
            {"role": "system", "content": "You are a helpful data quality assistant for futures datasets."}
        ]

    # (AI Enrich button removed; enrichment should be run offline script)

    # --- Input on top ---
    user_prompt = st.chat_input("Ask about the data or quality checks…")

    if user_prompt:
        # --- Retrieval-Augmented Generation (RAG) ---
        # Fetch top-N similar rows from the vector store
        N_RESULTS = 10
        try:
            rag = rag_query([user_prompt], n_results=N_RESULTS)
            metas = rag.get("metadatas", [[]])[0]
            dists = rag.get("distances", [[]])[0]
        except Exception as e:
            metas = []
            st.warning(f"Chroma query failed: {e}")

        # Build context text for the LLM
        ctx_lines = []
        src_refs = []
        import json, copy
        for m, dist in zip(metas, dists):
            symbol = m.get("Symbol", "?")
            date = m.get("Date", "?")
            score = 1 - float(dist) if dist is not None else None
            row_plus = copy.deepcopy(m)
            row_plus["similarity"] = round(score, 4) if score is not None else None
            ctx_lines.append(json.dumps(row_plus, default=str, indent=2))
            src_refs.append(f"{symbol} {date} – {score:.2f}" if score is not None else f"{symbol} {date}")
        context_text = "\n".join(ctx_lines)

        # Assemble message list with ephemeral context via external template
        system_prompt = TEMPLATE_CHAT.replace("{{context}}", context_text)
        messages_to_send = (
            st.session_state.chat_msgs
            + [{"role": "system", "content": system_prompt}]
            + [{"role": "user", "content": user_prompt}]
        )

        # --- DEBUG: print composed prompt to terminal for inspection ---
        def _pretty(msgs):
            parts = []
            for m in msgs:
                role = m.get("role", "?").upper()
                content = m.get("content", "").strip()
                parts.append(f"\n[{role}]\n{content}\n")
            return "\n".join(parts)

        print("\n" + "=" * 40 + " COMPILED PROMPT " + "=" * 40)
        print(_pretty(messages_to_send))
        print("=" * 94 + "\n")

        # Call OpenAI Chat
        if OPENAI_API_KEY:
            with st.spinner("Thinking…"):
                try:
                    resp = oai.chat(messages_to_send)
                    reply_main = resp.choices[0].message.content.strip()
                except Exception as e:
                    reply_main = f"Error: {e}"
        else:
            reply_main = "OpenAI key not set."

        # Append sources beneath answer
        if src_refs:
            sources_md = "\n\n**Sources:**\n" + "\n".join(f"- {r}" for r in src_refs)
        else:
            sources_md = ""

        full_reply = reply_main + sources_md

        # Update chat history (user + assistant) – omit context message for cleanliness
        st.session_state.chat_msgs.append({"role": "user", "content": user_prompt})
        st.session_state.chat_msgs.append({"role": "assistant", "content": full_reply})

    # --- Render history newest → oldest under the input ---
    for m in reversed(st.session_state.chat_msgs[1:]):  # skip system
        with st.chat_message(m["role"]):
            st.markdown(m["content"]) 