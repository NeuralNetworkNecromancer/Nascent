"""Unified Data-Quality Dashboard – upload, configure, analyse, download."""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from app.utils.caching import load_data
from app.utils.config import get_config, set_config, DEFAULT_SEVERITIES
from src import eda_utils as eu

DESCRIPTIONS = eu.DESCRIPTIONS
DEFAULT_SEVERITIES = DEFAULT_SEVERITIES
CHECK_FUNCTIONS = eu.CHECK_FUNCTIONS

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
    vol_factor = st.select_slider(
        "Extreme volume factor (× median)",
        options=[2, 5, 10, 20],
        value=int(cfg.get("volume_factor", 10)),
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
flagged_rows = df_flags[union_mask].reset_index(drop=True)

# ------------ Plot -------------

df_plot = df_view.copy()
df_plot["Date_dt"] = pd.to_datetime(df_plot["Date"].astype(str), format="%Y%m%d", errors="coerce")

# Helper to classify highest severity for plotting
def _sev_level(row):
    if row["critical_flags"] > 0:
        return "critical"
    if row["major_flags"] > 0:
        return "major"
    if row["minor_flags"] > 0:
        return "minor"
    return "none"

df_plot = df_plot.join(df_flags[["critical_flags", "major_flags", "minor_flags"]])
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

st.altair_chart(chart, use_container_width=True)

# ---------- Additional Visualisations ----------

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
    ).properties(height=220)
)

# Treemap-style horizontal bar per severity with symbol rectangles

sym_df = (
    df_flags[["Symbol", "critical_flags", "major_flags", "minor_flags"]]
    .groupby("Symbol", as_index=False)
    .agg(rows=("Symbol", "size"),
         crit=("critical_flags", "sum"),
         maj =("major_flags", "sum"),
         min =("minor_flags", "sum"))
)

sym_df["worst"] = sym_df.apply(lambda r: "critical" if r.crit else ("major" if r.maj else ("minor" if r.min else "none")), axis=1)

treemap = (
    alt.Chart(sym_df)
    .transform_window(row_number='row_number()')  # ensures stable ordering
    .mark_bar()
    .encode(
        y=alt.Y('worst:N', title='Worst severity', sort=['critical','major','minor','none']),
        x=alt.X('rows:Q', title='Rows'),
        color=alt.Color('worst:N', scale=alt.Scale(domain=list(sev_colors), range=list(sev_colors.values())), legend=None),
        tooltip=["Symbol", "rows", "worst"]
    ).properties(height=160)
)

st.altair_chart(stack_chart, use_container_width=True)
st.altair_chart(treemap, use_container_width=True)

st.subheader("Flagged rows")
if flagged_rows.empty:
    st.success("No rows failed the selected checks 🎉")
else:
    st.write(f"Rows flagged: {len(flagged_rows):,}")
    st.dataframe(flagged_rows)
    csv = flagged_rows.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download flagged CSV", csv, "flagged_rows.csv", "text/csv")

st.subheader("Counts per selected check")
cols = st.columns(min(4, len(selected)))
for i, name in enumerate(selected):
    cols[i % len(cols)].metric(label=name, value=f"{check_counts[name]:,}")

# Show severity counts summary
st.subheader("Severity flag counts (for selected checks)")
st.write({sev: int(flags_df[f"{sev}_flags"].sum()) for sev in ["critical", "major", "minor"]}) 