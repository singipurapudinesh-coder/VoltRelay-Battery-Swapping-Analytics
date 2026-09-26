from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from src import config


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

TABLES_DIR = config.TABLES_DIR
FIGURES_DIR = config.FIGURES_DIR

MONTHLY_FILE = TABLES_DIR / "monthly_network_kpis.csv"
CITY_FILE = TABLES_DIR / "city_network_kpis.csv"
STATION_FILE = TABLES_DIR / "station_network_kpis.csv"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# LOAD KPI DATA
# --------------------------------------------------

def load_kpi_data():

    monthly = pd.read_csv(MONTHLY_FILE)
    city = pd.read_csv(CITY_FILE)
    station = pd.read_csv(STATION_FILE)

    monthly["month"] = pd.to_datetime(monthly["month"])

    print("KPI files loaded successfully.")
    print(f"Monthly records: {len(monthly)}")
    print(f"Cities analyzed: {len(city)}")
    print(f"Stations analyzed: {len(station)}")

    return monthly, city, station


# --------------------------------------------------
# 1. MONTHLY SWAP VOLUME
# --------------------------------------------------

def plot_monthly_swaps(monthly):

    plt.figure(figsize=(13, 6))

    plt.plot(
        monthly["month"],
        monthly["total_attempts"],
        marker="o",
        label="Total Attempts"
    )

    plt.plot(
        monthly["month"],
        monthly["completed_swaps"],
        marker="s",
        label="Completed Swaps"
    )

    plt.title("VoltRelay Monthly Swap Volume")
    plt.xlabel("Month")
    plt.ylabel("Number of Swaps")

    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "monthly_swap_volume.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# 2. MONTHLY FAILURE AND ABANDONMENT RATES
# --------------------------------------------------

def plot_monthly_failure_rates(monthly):

    plt.figure(figsize=(13, 6))

    plt.plot(
        monthly["month"],
        monthly["failure_rate_pct"],
        marker="o",
        label="Failure Rate"
    )

    plt.plot(
        monthly["month"],
        monthly["abandonment_rate_pct"],
        marker="s",
        label="Abandonment Rate"
    )

    plt.title("Monthly Failure and Abandonment Rates")
    plt.xlabel("Month")
    plt.ylabel("Rate (%)")

    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "monthly_failure_abandonment.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# 3. MONTHLY COMPLETED REVENUE
# --------------------------------------------------

def plot_monthly_revenue(monthly):

    plt.figure(figsize=(13, 6))

    plt.bar(
        monthly["month"].dt.strftime("%Y-%m"),
        monthly["completed_revenue_inr"]
    )

    plt.title("Monthly Completed-Swap Revenue")
    plt.xlabel("Month")
    plt.ylabel("Revenue (INR)")

    plt.xticks(rotation=60)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "monthly_revenue.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# 4. CITY-LEVEL FAILURE RATES
# --------------------------------------------------

def plot_city_failure_rates(city):

    city_sorted = city.sort_values(
        "failure_rate_pct",
        ascending=True
    )

    plt.figure(figsize=(10, 6))

    plt.barh(
        city_sorted["city"],
        city_sorted["failure_rate_pct"]
    )

    plt.title("Failure Rate by City")
    plt.xlabel("Failure Rate (%)")
    plt.ylabel("City")

    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "city_failure_rates.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# 5. CITY-LEVEL COMPLETED REVENUE
# --------------------------------------------------

def plot_city_revenue(city):

    city_sorted = city.sort_values(
        "completed_revenue_inr",
        ascending=True
    )

    plt.figure(figsize=(10, 6))

    plt.barh(
        city_sorted["city"],
        city_sorted["completed_revenue_inr"]
    )

    plt.title("Completed-Swap Revenue by City")
    plt.xlabel("Revenue (INR)")
    plt.ylabel("City")

    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "city_revenue.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# 6. TOP 10 STATIONS BY COMPLETED SWAPS
# --------------------------------------------------

def plot_top_stations(station):

    top_stations = station.nlargest(
        10,
        "completed_swaps"
    ).sort_values("completed_swaps")

    plt.figure(figsize=(12, 7))

    plt.barh(
        top_stations["station_id"],
        top_stations["completed_swaps"]
    )

    plt.title("Top 10 Stations by Completed Swaps")
    plt.xlabel("Completed Swaps")
    plt.ylabel("Station ID")

    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    output = FIGURES_DIR / "top_10_stations.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("VOLTRELAY KPI VISUALIZATION")
    print("=" * 65)

    monthly, city, station = load_kpi_data()

    plot_monthly_swaps(monthly)
    plot_monthly_failure_rates(monthly)
    plot_monthly_revenue(monthly)
    plot_city_failure_rates(city)
    plot_city_revenue(city)
    plot_top_stations(station)

    print("\n" + "=" * 65)
    print("KPI VISUALIZATION COMPLETED")
    print(f"Charts saved in: {FIGURES_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()