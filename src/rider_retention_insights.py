
from pathlib import Path
import pandas as pd
import numpy as np

from src import config


# ============================================================
# VOLTRELAY - RIDER RETENTION BUSINESS INSIGHTS
# ============================================================

TABLES_DIR = config.TABLES_DIR
FINDINGS_DIR = config.FINDINGS_DIR

FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = FINDINGS_DIR / "rider_retention_business_insights.txt"
OUTPUT_CSV = FINDINGS_DIR / "rider_retention_key_metrics.csv"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_csv(filename):
    """Load a CSV from the analysis tables directory."""

    file_path = TABLES_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}\n"
            "Run rider_retention_analysis.py first."
        )

    return pd.read_csv(file_path)


def get_column(df, candidates):
    """Find a column using possible column names."""

    for column in candidates:
        if column in df.columns:
            return column

    raise KeyError(
        f"Could not find any of these columns: {candidates}\n"
        f"Available columns: {list(df.columns)}"
    )


def format_inr(value):
    """Format a number as Indian Rupees."""

    return f"₹{value:,.2f}"


def add_finding(findings, category, metric, value, interpretation):
    """Add a structured finding."""

    findings.append({
        "category": category,
        "metric": metric,
        "value": value,
        "interpretation": interpretation
    })


# ============================================================
# 1. RIDER ENGAGEMENT INSIGHTS
# ============================================================


def analyze_rider_segments(findings):

    df = load_csv("rider_segment_summary.csv")

    # Match the actual column names in your CSV
    segment_col = get_column(
        df,
        ["rider_segment", "segment"]
    )

    count_col = get_column(
        df,
        ["rider_count"]
    )

    swaps_col = get_column(
        df,
        ["completed_swaps", "total_completed_swaps", "swap_count"]
    )

    revenue_col = get_column(
        df,
        ["total_revenue_inr", "revenue_inr", "completed_revenue_inr"]
    )

    df[count_col] = pd.to_numeric(
        df[count_col], errors="coerce"
    ).fillna(0)

    df[swaps_col] = pd.to_numeric(
        df[swaps_col], errors="coerce"
    ).fillna(0)

    df[revenue_col] = pd.to_numeric(
        df[revenue_col], errors="coerce"
    ).fillna(0)

    total_riders = df[count_col].sum()
    total_revenue = df[revenue_col].sum()
    total_swaps = df[swaps_col].sum()

    add_finding(
        findings,
        "Engagement",
        "Total riders in segment summary",
        int(total_riders),
        "Total riders represented in the engagement segment summary."
    )

    add_finding(
        findings,
        "Engagement",
        "Completed swaps",
        int(total_swaps),
        "Completed swaps represented in the engagement segment summary."
    )

    add_finding(
        findings,
        "Engagement",
        "Completed swap revenue",
        round(total_revenue, 2),
        "Revenue from completed swaps; this is not profit."
    )

    # Calculate each segment's contribution
    for _, row in df.iterrows():

        segment = str(row[segment_col])
        rider_count = int(row[count_col])
        swaps = int(row[swaps_col])
        revenue = float(row[revenue_col])

        rider_share = (
            rider_count / total_riders * 100
            if total_riders > 0 else 0
        )

        revenue_share = (
            revenue / total_revenue * 100
            if total_revenue > 0 else 0
        )

        add_finding(
            findings,
            "Engagement Segment",
            f"{segment} - rider count",
            rider_count,
            f"{rider_share:.2f}% of riders in the segment summary."
        )

        add_finding(
            findings,
            "Engagement Segment",
            f"{segment} - completed swaps",
            swaps,
            f"{swaps:,} completed swaps attributed to this segment."
        )

        add_finding(
            findings,
            "Engagement Segment",
            f"{segment} - revenue contribution",
            round(revenue, 2),
            f"{revenue_share:.2f}% of completed swap revenue."
        )

# ============================================================
# 2. MONTHLY RIDER GROWTH
# ============================================================

def analyze_monthly_growth(findings):

    df = load_csv("monthly_active_riders.csv")

    month_col = get_column(df, ["month"])
    active_col = get_column(
    df,
    ["active_riders", "monthly_active_riders"]
)

    df[month_col] = pd.to_datetime(df[month_col], errors="coerce")
    df[active_col] = pd.to_numeric(df[active_col], errors="coerce")

    df = (
        df.dropna(subset=[month_col, active_col])
        .sort_values(month_col)
        .drop_duplicates(subset=[month_col], keep="last")
    )

    if df.empty:
        return

    first = df.iloc[0]
    last = df.iloc[-1]

    first_active = int(first[active_col])
    last_active = int(last[active_col])

    growth = (
        (last_active - first_active) / first_active * 100
        if first_active > 0 else 0
    )

    add_finding(
        findings,
        "Growth",
        "First recorded monthly active riders",
        first_active,
        f"Month: {first[month_col].strftime('%Y-%m')}."
    )

    add_finding(
        findings,
        "Growth",
        "Latest monthly active riders",
        last_active,
        f"Month: {last[month_col].strftime('%Y-%m')}."
    )

    add_finding(
        findings,
        "Growth",
        "Change from first to latest month (%)",
        round(growth, 2),
        "Describes change in monthly active riders across the observed period; "
        "it does not establish the cause of growth."
    )

    # Month-over-month growth
    df["mom_growth_pct"] = (
        df[active_col].pct_change() * 100
    )

    valid_growth = df.dropna(subset=["mom_growth_pct"])

    if not valid_growth.empty:

        latest_growth = valid_growth.iloc[-1]["mom_growth_pct"]

        add_finding(
            findings,
            "Growth",
            "Latest month-over-month active rider growth (%)",
            round(float(latest_growth), 2),
            "Change in active riders from the previous recorded month."
        )


# ============================================================
# 3. COHORT RETENTION INSIGHTS
# ============================================================

def analyze_cohort_retention(findings):

    df = load_csv("rider_cohort_retention.csv")

    cohort_col = get_column(df, ["cohort_month"])
    month_num_col = get_column(
        df,
        ["months_since_cohort", "month_number", "cohort_age_months"]
    )

    retention_col = get_column(
    df,
    [
        "retention_rate",
        "retention_pct",
        "retention_percentage",
        "retention_rate_pct"
    ]
)

    df[cohort_col] = pd.to_datetime(
        df[cohort_col],
        errors="coerce"
    )

    df[month_num_col] = pd.to_numeric(
        df[month_num_col],
        errors="coerce"
    )

    df[retention_col] = pd.to_numeric(
        df[retention_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=[cohort_col, month_num_col, retention_col]
    )

    if df.empty:
        return

    # Convert decimal retention rates to percentage values.
    if df[retention_col].max() <= 1:
        df[retention_col] *= 100

    # Use January 2024 cohort as an illustrative example
    # if that cohort is present.

    january_cohort = df[
        df[cohort_col].dt.strftime("%Y-%m") == "2024-01"
    ]

    if not january_cohort.empty:

        for month_num in [1, 3, 6, 12]:

            matching = january_cohort[
                january_cohort[month_num_col] == month_num
            ]

            if not matching.empty:

                retention = float(
                    matching.iloc[0][retention_col]
                )

                add_finding(
                    findings,
                    "Cohort Retention",
                    f"January 2024 cohort month {month_num} retention (%)",
                    round(retention, 2),
                    "Percentage of the January 2024 cohort retained "
                    "at the specified cohort age."
                )

    # Average retention by cohort age.
    average_retention = (
        df.groupby(month_num_col)[retention_col]
        .mean()
        .sort_index()
    )

    for month_num, retention in average_retention.items():

        add_finding(
            findings,
            "Cohort Retention",
            f"Average retention at month {int(month_num)} (%)",
            round(float(retention), 2),
            "Unweighted average of available cohort retention rates "
            "at this age. Cohort sizes may differ."
        )


# ============================================================
# 4. INACTIVITY / CHURN PROXY INSIGHTS
# ============================================================

def analyze_inactivity(findings):

    df = load_csv("rider_churn_summary.csv")

    status_col = get_column(
        df,
        ["churn_status", "activity_status", "rider_status"]
    )

    count_col = get_column(
        df,
        ["rider_count", "rider_count_unique", "count"]
    )

    df[count_col] = pd.to_numeric(
        df[count_col],
        errors="coerce"
    ).fillna(0)

    df[status_col] = df[status_col].astype(str)

    total_riders = df[count_col].sum()

    inactive_mask = df[status_col].str.contains(
        "inactive",
        case=False,
        na=False
    )

    active_mask = df[status_col].str.contains(
        "active",
        case=False,
        na=False
    ) & ~inactive_mask

    inactive_count = df.loc[inactive_mask, count_col].sum()
    active_count = df.loc[active_mask, count_col].sum()

    if total_riders > 0:

        inactivity_rate = (
            inactive_count / total_riders * 100
        )

        add_finding(
            findings,
            "Inactivity",
            "Riders classified inactive (%)",
            round(inactivity_rate, 2),
            "Inactivity proxy based on the existing analysis cutoff; "
            "not a confirmed permanent churn rate."
        )

        add_finding(
            findings,
            "Inactivity",
            "Riders classified inactive",
            int(inactive_count),
            "Riders classified as inactive in the analysis output."
        )

        add_finding(
            findings,
            "Inactivity",
            "Riders classified active",
            int(active_count),
            "Riders classified active in the analysis output."
        )


# ============================================================
# 5. BUSINESS RECOMMENDATIONS
# ============================================================

def generate_recommendations(findings):

    recommendations = []

    recommendations.append(
        "1. Rider reactivation: Identify riders classified as inactive "
        "and evaluate targeted reactivation campaigns. Track completed "
        "swaps after outreach rather than relying only on campaign clicks."
    )

    recommendations.append(
        "2. Retention monitoring: Track monthly active riders and cohort "
        "retention together. Compare cohorts at the same age because "
        "recent cohorts have had less time to mature."
    )

    recommendations.append(
        "3. Engagement segmentation: Design separate engagement strategies "
        "for frequent, regular, occasional, and one-time riders. Measure "
        "incremental completed swaps and revenue for each campaign."
    )

    recommendations.append(
        "4. Revenue measurement: Treat completed swap charges as revenue "
        "rather than profit. Include operating costs, discounts, partner "
        "payments, battery depreciation, and station costs before assessing "
        "profitability."
    )

    recommendations.append(
        "5. Data-driven experimentation: Test retention initiatives using "
        "appropriate comparison groups where feasible. Observational "
        "patterns alone do not establish that a campaign or operational "
        "change caused rider retention."
    )

    recommendations.append(
        "6. Privacy: Use aggregated rider segments for reporting and avoid "
        "including personally identifying rider information in public "
        "dashboards or hackathon materials."
    )

    return recommendations


# ============================================================
# 6. SAVE OUTPUTS
# ============================================================

def save_findings(findings, recommendations):

    findings_df = pd.DataFrame(findings)

    findings_df.to_csv(
        OUTPUT_CSV,
        index=False
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "VOLTRELAY BATTERY SWAPPING ANALYTICS\n"
            "RIDER RETENTION BUSINESS INSIGHTS\n"
            "=" * 60 + "\n\n"
        )

        file.write(
            "Note: Findings are calculated from the project's "
            "synthetic dataset and existing analysis outputs. "
            "They should not be interpreted as verified real-world "
            "VoltRelay business performance.\n\n"
        )

        file.write("KEY FINDINGS\n")
        file.write("-" * 60 + "\n\n")

        for finding in findings:

            file.write(
                f"Category: {finding['category']}\n"
                f"Metric: {finding['metric']}\n"
                f"Value: {finding['value']}\n"
                f"Interpretation: {finding['interpretation']}\n\n"
            )

        file.write("\nBUSINESS RECOMMENDATIONS\n")
        file.write("-" * 60 + "\n\n")

        for recommendation in recommendations:
            file.write(recommendation + "\n\n")

        file.write(
            "\nLIMITATIONS\n"
            "- Inactivity is a proxy, not confirmed permanent churn.\n"
            "- Revenue means completed swap charges, not profit.\n"
            "- Observational associations do not prove causation.\n"
            "- Results reflect the supplied synthetic dataset.\n"
        )

    print(f"\nSaved findings CSV: {OUTPUT_CSV}")
    print(f"Saved insights report: {OUTPUT_FILE}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 60)
    print("VOLTRELAY RIDER RETENTION BUSINESS INSIGHTS")
    print("=" * 60)

    findings = []

    analyze_rider_segments(findings)
    analyze_monthly_growth(findings)
    analyze_cohort_retention(findings)
    analyze_inactivity(findings)

    recommendations = generate_recommendations(findings)

    save_findings(findings, recommendations)

    print("\nKey findings generated:", len(findings))
    print("Business recommendations generated:", len(recommendations))

    print("\nRider retention insights completed successfully.")


if __name__ == "__main__":
    main()