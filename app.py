import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
    
st.set_page_config(page_title="Automated Insight Generation", page_icon="📊", layout="wide")

st.title("📊 Automated Insight Generation")
st.caption("A general-purpose healthcare analytics engine: trends, outliers, correlations, and data-driven explanations.")

REQUIRED = ["month", "district", "anc_coverage", "institutional_delivery", "immunization", "high_risk_cases"]
INDICATORS = ["anc_coverage", "institutional_delivery", "immunization", "high_risk_cases"]
LABELS = {
    "anc_coverage": "ANC Coverage (%)",
    "institutional_delivery": "Institutional Delivery (%)",
    "immunization": "Immunization (%)",
    "high_risk_cases": "High-risk Cases (count)",
}

def load_and_validate(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv(Path(__file__).parent / "healthcare_data.csv")
    df.columns = [c.strip().lower() for c in df.columns]
    missing_columns = [c for c in REQUIRED if c not in df.columns]
    if missing_columns:
        raise ValueError("Missing required columns: " + ", ".join(missing_columns))
    df = df[REQUIRED].copy()
    df["month"] = df["month"].astype(str).str.strip()
    df["district"] = df["district"].astype(str).str.strip()
    for col in INDICATORS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["month_date"] = pd.to_datetime(df["month"], errors="coerce")
    df = df.dropna(subset=["month_date", "district"]).sort_values(["district", "month_date"])
    return df

def severity_for_change(change):
    # Severity is derived from the configured significant-change threshold.
    magnitude = abs(change)
    if magnitude >= 2 * st.session_state.trend_threshold:
        return "High"
    if magnitude >= st.session_state.trend_threshold:
        return "Medium"
    return "Low"

def build_insights(df, trend_threshold, outlier_method, z_threshold, corr_threshold):
    insights = []
    def add(kind, indicator, entity, period, value, prev_value, change_pct, severity, explanation, metric=None):
        insights.append({
            "insight_id": f"INS-{len(insights)+1:04d}",
            "type": kind,
            "indicator": indicator,
            "entity": entity,
            "period": period,
            "value": value,
            "prev_value": prev_value,
            "change_pct": change_pct,
            "severity": severity,
            "explanation": explanation,
            "metric": metric if metric is not None else value,
        })

    # Trends: compare each district's current row with its previous available month.
    for district, group in df.groupby("district"):
        group = group.sort_values("month_date")
        for indicator in INDICATORS:
            vals = group[["month", "month_date", indicator]].dropna().reset_index(drop=True)
            for i in range(1, len(vals)):
                prev, cur = vals.iloc[i-1], vals.iloc[i]
                if prev[indicator] == 0:
                    continue
                change = (cur[indicator] - prev[indicator]) / abs(prev[indicator]) * 100
                if abs(change) >= trend_threshold:
                    direction = "increased" if change > 0 else "dropped"
                    unit = "%" if indicator != "high_risk_cases" else " cases"
                    explanation = (
                        f"{LABELS[indicator]} in {district} {direction} by {abs(change):.1f}% "
                        f"from {prev['month']} to {cur['month']}, exceeding the "
                        f"{trend_threshold:.1f}% significant-change threshold."
                    )
                    add("trend", indicator, district, cur["month"], float(cur[indicator]),
                        float(prev[indicator]), round(float(change), 1),
                        "High" if abs(change) >= 2*trend_threshold else "Medium",
                        explanation)

    # Outliers: IQR is calculated across all available district-month rows for each indicator.
    for indicator in INDICATORS:
        values = df[indicator].dropna()
        if len(values) < 4:
            continue
        if outlier_method == "IQR":
            q1, q3 = values.quantile(.25), values.quantile(.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
            mask = df[indicator].notna() & ((df[indicator] < lower) | (df[indicator] > upper))
            bounds = f"IQR bounds are {lower:.2f} to {upper:.2f}"
        else:
            mean, std = values.mean(), values.std(ddof=0)
            if std == 0 or np.isnan(std):
                continue
            zscores = (df[indicator] - mean) / std
            mask = zscores.abs() >= z_threshold
            bounds = f"absolute Z-score is at least {z_threshold:.2f}"
        for _, row in df.loc[mask].iterrows():
            value = float(row[indicator])
            median = float(values.median())
            deviation = abs(value - median) / (abs(median) if median else 1) * 100
            severity = "High" if deviation >= 30 else "Medium" if deviation >= 15 else "Low"
            explanation = (f"{LABELS[indicator]} for {row['district']} in {row['month']} is "
                           f"{value:g}, outside the expected range ({bounds}); review this observation.")
            add("outlier", indicator, row["district"], row["month"], value, None, None,
                severity, explanation)

    # Correlations across numerical indicators; warn in UI/README that the sample is small.
    corr = df[INDICATORS].corr(method="pearson")
    for i, first in enumerate(INDICATORS):
        for second in INDICATORS[i+1:]:
            r = corr.loc[first, second]
            if pd.notna(r) and abs(r) >= corr_threshold:
                severity = "High" if abs(r) >= .9 else "Medium"
                explanation = (f"{LABELS[first]} and {LABELS[second]} have a Pearson correlation "
                               f"of {r:.2f} across the available rows (threshold ±{corr_threshold:.2f}). "
                               "Correlation does not establish causation; this small sample may be unstable.")
                add("correlation", f"{first}:{second}", "All districts", "All available months",
                    round(float(r), 3), None, None, severity, explanation, metric=round(float(r), 3))
    return pd.DataFrame(insights, columns=[
        "insight_id","type","indicator","entity","period","value","prev_value",
        "change_pct","severity","explanation","metric"
    ]), corr

uploaded = st.sidebar.file_uploader("Upload healthcare CSV (optional)", type=["csv"])
try:
    data = load_and_validate(uploaded)
except Exception as e:
    st.error(f"Could not load dataset: {e}")
    st.stop()

st.sidebar.header("Live filters")
district_options = sorted(data["district"].unique().tolist())
month_options = sorted(data["month"].unique().tolist())
selected_districts = st.sidebar.multiselect("District", district_options, default=district_options)
selected_months = st.sidebar.multiselect("Month", month_options, default=month_options)
selected_indicators = st.sidebar.multiselect("Indicator", INDICATORS, default=INDICATORS, format_func=lambda x: LABELS[x])
st.sidebar.header("Detection thresholds")
trend_threshold = st.sidebar.slider("Significant trend change (%)", 1, 100, 10, 1)
outlier_method = st.sidebar.selectbox("Outlier method", ["IQR", "Z-score"])
z_threshold = st.sidebar.slider("Absolute Z-score threshold", 1.0, 5.0, 3.0, 0.5)
corr_threshold = st.sidebar.slider("Correlation threshold (|r|)", 0.1, 1.0, 0.70, 0.05)

filtered = data[
    data["district"].isin(selected_districts) & data["month"].isin(selected_months)
].copy()
if not selected_indicators:
    st.warning("Select at least one indicator to display indicator-specific charts.")
display_indicators = selected_indicators or INDICATORS

with st.expander("Data preview and validation", expanded=False):
    st.subheader("CSV head()")
    st.dataframe(data[REQUIRED].head(), use_container_width=True)
    st.subheader("Data info")
    info = pd.DataFrame({"column": data[REQUIRED].columns, "dtype": [str(data[c].dtype) for c in REQUIRED],
                         "non_null_count": [int(data[c].notna().sum()) for c in REQUIRED]})
    st.dataframe(info, use_container_width=True)
    st.subheader("Missing values per column")
    st.dataframe(data[REQUIRED].isna().sum().rename("missing_count").reset_index().rename(columns={"index":"column"}), use_container_width=True)
    

insights_all, corr_all = build_insights(data, trend_threshold, outlier_method, z_threshold, corr_threshold)
# Filter insights live by selected district/month/indicator; correlation rows remain visible for selected indicator pairs.
if not insights_all.empty:
    shown = insights_all[
        ((insights_all["entity"].isin(selected_districts)) | (insights_all["entity"] == "All districts")) &
        ((insights_all["period"].isin(selected_months)) | (insights_all["period"] == "All available months")) &
        (insights_all["indicator"].apply(lambda x: any(ind in x.split(":") for ind in display_indicators)))
    ].copy()
else:
    shown = insights_all.copy()

st.subheader("Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows in filtered data", len(filtered))
c2.metric("Districts", filtered["district"].nunique())
c3.metric("Insights shown", len(shown))
c4.metric("High severity", int((shown["severity"] == "High").sum()) if not shown.empty else 0)

st.subheader("Automated insights")
if shown.empty:
    st.info("No insights match the current filters and thresholds.")
else:
    st.dataframe(shown.drop(columns=["metric"]), use_container_width=True, hide_index=True)
    st.download_button("Download insights CSV", data=shown.drop(columns=["metric"]).to_csv(index=False).encode("utf-8"),
                       file_name="insights.csv", mime="text/csv")
    st.download_button("Download all insights CSV", data=insights_all.drop(columns=["metric"]).to_csv(index=False).encode("utf-8"),
                       file_name="all_insights.csv", mime="text/csv")

left, right = st.columns(2)
with left:
    st.subheader("Severity counts")
    if shown.empty:
        st.info("No severity counts to chart.")
    else:
        counts = shown["severity"].value_counts().reindex(["Low","Medium","High"], fill_value=0).rename_axis("severity").reset_index(name="count")
        fig = px.bar(counts, x="severity", y="count", color="severity", title="Insights by severity")
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Pearson correlation heatmap")
    corr_filtered = filtered[display_indicators].corr(method="pearson")
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(corr_filtered, annot=True, cmap="coolwarm", vmin=-1, vmax=1, center=0, ax=ax)
    ax.set_title("Correlation across filtered rows")
    st.pyplot(fig)
    st.caption("Only 12 sample rows (2 months × 6 districts): correlations are fragile and do not imply causation.")

# ---------------- IQR OUTLIER DETECTION RESULTS ----------------

st.subheader("IQR Outlier Detection Results")

iqr_results = []

for indicator in INDICATORS:
    values = data[indicator].dropna()

    if len(values) < 4:
        continue

    # Calculate quartiles and IQR
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    # Detect values outside IQR bounds
    mask = (
        data[indicator].notna()
        & (
            (data[indicator] < lower_bound)
            | (data[indicator] > upper_bound)
        )
    )

    outliers = data.loc[mask]

    for _, row in outliers.iterrows():
        iqr_results.append({
            "District": row["district"],
            "Month": row["month"],
            "Indicator": LABELS[indicator],
            "Value": row[indicator],
            "Q1": round(q1, 2),
            "Q3": round(q3, 2),
            "IQR": round(iqr, 2),
            "Lower Bound": round(lower_bound, 2),
            "Upper Bound": round(upper_bound, 2)
        })

if iqr_results:
    iqr_df = pd.DataFrame(iqr_results)

    # Apply the current dashboard filters
    iqr_df = iqr_df[
        iqr_df["District"].isin(selected_districts)
        & iqr_df["Month"].isin(selected_months)
        & iqr_df["Indicator"].isin(
            [LABELS[ind] for ind in selected_indicators]
        )
    ]

    if not iqr_df.empty:
        st.success(
            f"Detected {len(iqr_df)} IQR outlier(s)."
        )
        st.dataframe(
            iqr_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download IQR outliers CSV",
            data=iqr_df.to_csv(index=False).encode("utf-8"),
            file_name="iqr_outliers.csv",
            mime="text/csv"
        )
    else:
        st.info(
            "No IQR outliers match the current filters. "
            "Select all months, districts and indicators."
        )
else:
    st.info("No IQR outliers detected in the dataset.")

# ---------------------------------------------------------------

st.subheader("Per-district line chart")
if not filtered.empty and display_indicators:
    chart_data = filtered.melt(id_vars=["month","month_date","district"], value_vars=display_indicators,
                               var_name="indicator", value_name="value")
    chart_data["indicator_label"] = chart_data["indicator"].map(LABELS)
    fig = px.line(chart_data, x="month_date", y="value", color="district", line_dash="indicator_label",
                  markers=True, title="Indicator values over time", hover_data=["month","indicator_label"])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for the selected filters.")

st.subheader("Correlation matrix (CSV)")
st.dataframe(corr_all.round(3), use_container_width=True)
st.download_button("Download correlation matrix CSV", data=corr_all.to_csv().encode("utf-8"),
                   file_name="correlation_matrix.csv", mime="text/csv")
