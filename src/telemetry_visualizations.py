
import pandas as pd
import matplotlib.pyplot as plt

from src import config


def load_data():

    tables = config.TABLES_DIR

    inventory = pd.read_csv(
        tables / "failure_by_inventory.csv"
    )

    temperature = pd.read_csv(
        tables / "failure_by_temperature.csv"
    )

    quarantine = pd.read_csv(
        tables / "failure_by_quarantine.csv"
    )

    return inventory, temperature, quarantine


def plot_inventory(inventory):

    df = inventory[
        inventory["inventory_group"] != "Unknown"
    ].copy()

    plt.figure(figsize=(10, 6))

    plt.bar(
        df["inventory_group"],
        df["failure_rate_pct"]
    )

    plt.title("Swap Failure Rate by Battery Inventory")
    plt.xlabel("Charged Battery Inventory")
    plt.ylabel("Failure Rate (%)")

    plt.xticks(rotation=15)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    output = config.FIGURES_DIR / "failure_by_inventory.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


def plot_temperature(temperature):

    df = temperature[
        temperature["temperature_group"] != "Unknown"
    ].copy()

    plt.figure(figsize=(10, 6))

    plt.bar(
        df["temperature_group"],
        df["failure_rate_pct"]
    )

    plt.title("Swap Failure Rate by Ambient Temperature")
    plt.xlabel("Ambient Temperature")
    plt.ylabel("Failure Rate (%)")

    plt.xticks(rotation=15)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    output = config.FIGURES_DIR / "failure_by_temperature.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


def plot_quarantine(quarantine):

    df = quarantine[
        quarantine["quarantine_group"] != "Unknown"
    ].copy()

    plt.figure(figsize=(10, 6))

    plt.bar(
        df["quarantine_group"],
        df["failure_rate_pct"]
    )

    plt.title("Swap Failure Rate by Quarantined Battery Packs")
    plt.xlabel("Quarantined Packs")
    plt.ylabel("Failure Rate (%)")

    plt.xticks(rotation=15)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    output = config.FIGURES_DIR / "failure_by_quarantine.png"

    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output}")


def main():

    print("\nVOLTRELAY TELEMETRY VISUALIZATION")

    config.FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    inventory, temperature, quarantine = load_data()

    plot_inventory(inventory)
    plot_temperature(temperature)
    plot_quarantine(quarantine)

    print("\nTelemetry visualizations completed.")


if __name__ == "__main__":
    main()