
"""
VoltRelay Battery Health Visualizations
----------------------------------------
Creates presentation-ready charts from battery health
analysis output tables.

Run from project root:
    python -m src.battery_health_visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt

from src import config


# ---------------------------------------------------------
# 1. LOAD ANALYSIS OUTPUTS
# ---------------------------------------------------------

def load_analysis_data():
    """Load the battery health analysis CSV files."""

    health_distribution = pd.read_csv(
        config.TABLES_DIR / "battery_health_distribution.csv"
    )

    health_by_type = pd.read_csv(
        config.TABLES_DIR / "battery_health_by_pack_type.csv"
    )

    swap_outcomes = pd.read_csv(
        config.TABLES_DIR / "swap_outcomes_by_incoming_soh.csv"
    )

    return health_distribution, health_by_type, swap_outcomes


# ---------------------------------------------------------
# 2. BATTERY HEALTH CATEGORY DISTRIBUTION
# ---------------------------------------------------------

def plot_health_distribution(health_distribution):
    """Visualize the number of batteries in each health category."""

    df = health_distribution.copy()

    # Exclude unknown categories if present.
    df = df[
        df["health_category"].notna()
        & (df["health_category"] != "Unknown")
    ]

    df = df.sort_values(
        "battery_count",
        ascending=False
    )

    if df.empty:
        print("Skipping health distribution: no valid categories.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(
        df["health_category"],
        df["battery_count"]
    )

    ax.set_title(
        "Battery Health Category Distribution",
        fontsize=16,
        fontweight="bold"
    )

    ax.set_xlabel("Battery Health Category", fontsize=12)
    ax.set_ylabel("Number of Batteries", fontsize=12)

    ax.bar_label(
        bars,
        labels=[
            f"{value:,.0f}"
            for value in df["battery_count"]
        ],
        padding=4,
        fontsize=10
    )

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.3
    )

    ax.tick_params(axis="x", rotation=15)

    plt.tight_layout()

    output_path = (
        config.FIGURES_DIR
        / "battery_health_distribution.png"
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_path}")


# ---------------------------------------------------------
# 3. AVERAGE SOH BY BATTERY PACK TYPE
# ---------------------------------------------------------

def plot_health_by_pack_type(health_by_type):
    """Compare initial and current SOH by battery pack type."""

    df = health_by_type.copy()

    df = df.dropna(
        subset=[
            "pack_type",
            "average_initial_soh_pct",
            "average_current_soh_pct"
        ]
    )

    if df.empty:
        print("Skipping pack type chart: no valid data.")
        return

    x = range(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    initial_bars = ax.bar(
        [i - width / 2 for i in x],
        df["average_initial_soh_pct"],
        width,
        label="Average Initial SOH"
    )

    current_bars = ax.bar(
        [i + width / 2 for i in x],
        df["average_current_soh_pct"],
        width,
        label="Average Current SOH"
    )

    ax.set_title(
        "Battery Health by Pack Type",
        fontsize=16,
        fontweight="bold"
    )

    ax.set_xlabel("Battery Pack Type", fontsize=12)
    ax.set_ylabel("Average State of Health (%)", fontsize=12)

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["pack_type"])

    ax.set_ylim(0, 110)

    ax.bar_label(
        initial_bars,
        fmt="%.1f%%",
        padding=3,
        fontsize=9
    )

    ax.bar_label(
        current_bars,
        fmt="%.1f%%",
        padding=3,
        fontsize=9
    )

    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()

    output_path = (
        config.FIGURES_DIR
        / "battery_health_by_pack_type.png"
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_path}")


# ---------------------------------------------------------
# 4. FAILURE RATE BY INCOMING BATTERY SOH
# ---------------------------------------------------------

def plot_failure_by_incoming_soh(swap_outcomes):
    """
    Plot swap failure rates by recorded incoming SOH.

    The Unknown category is excluded because it consists
    of events without usable incoming SOH and is dominated
    by system-error records in the current analysis.
    """

    df = swap_outcomes.copy()

    # Exclude Unknown from the main SOH comparison.
    df = df[
        df["incoming_soh_category"].isin([
            "Below 70%",
            "70-79.9%",
            "80-89.9%",
            "90%+",
        ])
    ].copy()

    category_order = [
        "Below 70%",
        "70-79.9%",
        "80-89.9%",
        "90%+",
    ]

    df["incoming_soh_category"] = pd.Categorical(
        df["incoming_soh_category"],
        categories=category_order,
        ordered=True
    )

    df = df.sort_values("incoming_soh_category")

    if df.empty:
        print("Skipping SOH failure chart: no valid data.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(
        df["incoming_soh_category"].astype(str),
        df["failure_rate_pct"]
    )

    ax.set_title(
        "Observed Swap Failure Rate by Incoming Battery SOH",
        fontsize=15,
        fontweight="bold"
    )

    ax.set_xlabel(
        "Recorded Incoming Battery SOH",
        fontsize=12
    )

    ax.set_ylabel(
        "Failure Rate (%)",
        fontsize=12
    )

    ax.bar_label(
        bars,
        labels=[
            f"{value:.2f}%"
            for value in df["failure_rate_pct"]
        ],
        padding=4,
        fontsize=10
    )

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.3
    )

    # Include a concise interpretation caveat.
    fig.text(
        0.5,
        0.01,
        "Descriptive association only; incoming SOH does not establish "
        "the cause of station inventory or system failures.",
        ha="center",
        fontsize=9,
        wrap=True
    )

    plt.tight_layout(rect=[0, 0.06, 1, 1])

    output_path = (
        config.FIGURES_DIR
        / "failure_by_incoming_battery_soh.png"
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_path}")


# ---------------------------------------------------------
# 5. MAIN PIPELINE
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("VOLTRELAY BATTERY HEALTH VISUALIZATION")
    print("=" * 60)

    config.FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    (
        health_distribution,
        health_by_type,
        swap_outcomes
    ) = load_analysis_data()

    plot_health_distribution(health_distribution)

    plot_health_by_pack_type(health_by_type)

    plot_failure_by_incoming_soh(swap_outcomes)

    print("\nBattery health visualizations completed.")
    print("Figures saved in:", config.FIGURES_DIR)


if __name__ == "__main__":
    main()