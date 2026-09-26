
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from src import config


# ============================================================
# VOLTRELAY - RIDER RETENTION VISUALIZATIONS
# ============================================================

TABLES_DIR = config.TABLES_DIR
FIGURES_DIR = config.FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPER FUNCTION
# ============================================================

def load_csv(filename):
    """Load a CSV file from the project's output tables folder."""

    file_path = TABLES_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}\n"
            "Run rider_retention_analysis.py first."
        )

    return pd.read_csv(file_path)


def save_figure(filename):
    """Save the current Matplotlib figure."""

    output_path = FIGURES_DIR / filename

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Saved: {output_path}")


# ============================================================
# 1. MONTHLY ACTIVE RIDERS
# ============================================================

def plot_monthly_active_riders():

    df = load_csv("monthly_active_riders.csv")

    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values("month")

    plt.figure(figsize=(13, 6))

    plt.plot(
        df["month"],
        df["monthly_active_riders"],
        marker="o",
        linewidth=2
    )

    plt.title(
        "VoltRelay Monthly Active Riders",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Month")
    plt.ylabel("Active Riders")

    plt.gca().yaxis.set_major_formatter(
        mtick.StrMethodFormatter("{x:,.0f}")
    )

    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.4)

    save_figure("monthly_active_riders.png")


# ============================================================
# 2. MONTHLY COMPLETED SWAP REVENUE
# ============================================================

def plot_monthly_revenue():

    df = load_csv("monthly_active_riders.csv")

    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values("month")

    # Revenue represents completed swap charges,
    # not profit or net operating income.

    revenue_column = "completed_revenue_inr"

    if revenue_column not in df.columns:
        raise KeyError(
            f"Column '{revenue_column}' not found in "
            "monthly_active_riders.csv. "
            f"Available columns: {list(df.columns)}"
        )

    plt.figure(figsize=(13, 6))

    plt.plot(
        df["month"],
        df[revenue_column],
        marker="o",
        linewidth=2
    )

    plt.title(
        "Monthly Revenue from Completed Swaps",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Month")
    plt.ylabel("Completed Swap Revenue (INR)")

    plt.gca().yaxis.set_major_formatter(
        mtick.StrMethodFormatter("₹{x:,.0f}")
    )

    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.4)

    save_figure("monthly_rider_revenue.png")


# ============================================================
# 3. RIDER ENGAGEMENT SEGMENTS
# ============================================================

def plot_rider_segments():

    df = load_csv("rider_segment_summary.csv")

    required_columns = {
    "rider_segment",
    "rider_count"
}


    missing = required_columns - set(df.columns)

    if missing:
        raise KeyError(
            f"Missing columns in rider_segment_summary.csv: {missing}"
        )

    df = df.sort_values(
        "rider_count",
        ascending=True
    )

    plt.figure(figsize=(11, 6))

    bars = plt.barh(
        df["rider_segment"].astype(str),
        df["rider_count"]
    )

    plt.title(
        "Rider Distribution by Engagement Segment",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Number of Riders")
    plt.ylabel("Rider Segment")

    plt.gca().xaxis.set_major_formatter(
        mtick.StrMethodFormatter("{x:,.0f}")
    )

    plt.bar_label(
        bars,
        fmt="%.0f",
        padding=4
    )

    plt.grid(
        axis="x",
        linestyle="--",
        alpha=0.3
    )

    save_figure("rider_segment_distribution.png")


# ============================================================
# 4. COHORT RETENTION HEATMAP
# ============================================================

def plot_cohort_retention():

    df = load_csv("rider_cohort_retention.csv")

    required_columns = {
    "cohort_month",
    "month_number",
    "retention_rate_pct"
}

    missing = required_columns - set(df.columns)

    if missing:
        raise KeyError(
            f"Missing columns in rider_cohort_retention.csv: {missing}"
        )

    df["cohort_month"] = pd.to_datetime(
        df["cohort_month"]
    )

    df["months_since_cohort"] = pd.to_numeric(
        df["month_number"],
        errors="coerce"
    )

    df["retention_rate"] = pd.to_numeric(
        df["retention_rate_pct"],
        errors="coerce"
    )

    pivot = df.pivot_table(
        index="cohort_month",
        columns="months_since_cohort",
        values="retention_rate",
        aggfunc="mean"
    )

    pivot = pivot.sort_index()

    # Convert rates from decimals to percentages
    # if the source CSV stores them between 0 and 1.

    # retention_rate_pct is already expressed as a percentage.
# Do not multiply by 100 again.

    plt.figure(figsize=(15, 8))

    image = plt.imshow(
        pivot,
        aspect="auto",
        interpolation="nearest"
    )

    plt.title(
        "Rider Cohort Retention Heatmap",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Months Since First Completed Swap")
    plt.ylabel("Rider Acquisition Cohort")

    plt.xticks(
        range(len(pivot.columns)),
        [int(x) for x in pivot.columns]
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index.strftime("%Y-%m")
    )

    colorbar = plt.colorbar(image)
    colorbar.set_label("Retention Rate (%)")

    plt.clim(0, 100)

    save_figure("rider_cohort_retention_heatmap.png")


# ============================================================
# 5. RIDER INACTIVITY / CHURN PROXY
# ============================================================

def plot_rider_churn():

    df = load_csv("rider_churn_summary.csv")

    required_columns = {
        "churn_status",
        "rider_count"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise KeyError(
            f"Missing columns in rider_churn_summary.csv: {missing}"
        )

    df = df.dropna(subset=["churn_status"])

    df = df.sort_values(
        "rider_count",
        ascending=False
    )

    plt.figure(figsize=(10, 6))

    bars = plt.bar(
        df["churn_status"].astype(str),
        df["rider_count"]
    )

    plt.title(
        "Rider Activity Status at Analysis End",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Activity Status")
    plt.ylabel("Number of Riders")

    plt.gca().yaxis.set_major_formatter(
        mtick.StrMethodFormatter("{x:,.0f}")
    )

    plt.bar_label(
        bars,
        fmt="%.0f",
        padding=4
    )

    plt.xticks(rotation=20)
    plt.grid(axis="y", linestyle="--", alpha=0.3)

    save_figure("rider_churn_distribution.png")


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():

    print("\n" + "=" * 60)
    print("VOLTRELAY RIDER RETENTION VISUALIZATION")
    print("=" * 60)

    plot_monthly_active_riders()
    plot_monthly_revenue()
    plot_rider_segments()
    plot_cohort_retention()
    plot_rider_churn()

    print("\nAll rider retention visualizations completed.")
    print(f"Figures saved in: {FIGURES_DIR}")


if __name__ == "__main__":
    main()