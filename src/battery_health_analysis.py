
"""
VoltRelay Battery Health Analysis
---------------------------------
Analyzes battery health, degradation, age, retirement,
and the association between incoming battery SOH and swap outcomes.

Run from project root:
    python -m src.battery_health_analysis
"""

import duckdb
import pandas as pd

from src import config


# ---------------------------------------------------------
# 1. DATABASE CONNECTION
# ---------------------------------------------------------

def connect_database():
    """Connect to the existing VoltRelay DuckDB database."""

    db_path = config.PROCESSED_DATA_DIR / "voltrelay.duckdb"

    connection = duckdb.connect(str(db_path))
    connection.execute("SET threads = 4")

    return connection


# ---------------------------------------------------------
# 2. LOAD BATTERY MASTER DATA
# ---------------------------------------------------------

def load_battery_data():
    """Load the battery master dataset."""

    batteries = pd.read_csv(
        config.BATTERIES_FILE,
        low_memory=False
    )

    # Standardize date fields.
    date_columns = [
        "manufacture_date",
        "commission_date",
        "retired_date",
    ]

    for column in date_columns:
        if column in batteries.columns:
            batteries[column] = pd.to_datetime(
                batteries[column],
                errors="coerce"
            )

    # Convert numeric fields safely.
    numeric_columns = [
        "rated_capacity_kwh",
        "purchase_cost_inr",
        "initial_soh_pct",
        "current_soh_pct",
    ]

    for column in numeric_columns:
        if column in batteries.columns:
            batteries[column] = pd.to_numeric(
                batteries[column],
                errors="coerce"
            )

    return batteries


# ---------------------------------------------------------
# 3. BATTERY MASTER HEALTH PROFILE
# ---------------------------------------------------------

def analyze_battery_health(batteries):
    """Summarize battery health and classify battery condition."""

    df = batteries.copy()

    # Retain the original values for data-quality checks.
    df["soh_change_pct"] = (
        df["current_soh_pct"] - df["initial_soh_pct"]
    )

    # Negative change indicates a reduction in reported SOH.
    df["reported_degradation_pct"] = (
        df["initial_soh_pct"] - df["current_soh_pct"]
    )

    # Classify only batteries with valid SOH values.
    conditions = [
        df["current_soh_pct"].isna(),
        df["current_soh_pct"] >= 90,
        df["current_soh_pct"] >= 80,
        df["current_soh_pct"] >= 70,
        df["current_soh_pct"] < 70,
    ]

    labels = [
        "Unknown",
        "Excellent (90%+)",
        "Good (80-89.9%)",
        "Aging (70-79.9%)",
        "Critical (<70%)",
    ]

    df["health_category"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="object"
    )

    for condition, label in zip(conditions, labels):
        df.loc[condition, "health_category"] = label

    # Battery age at retirement, or at the analysis cutoff
    # for batteries without a retirement date.
    analysis_date = pd.Timestamp("2025-06-30")

    df["age_days"] = (
        df["retired_date"].fillna(analysis_date)
        - df["commission_date"]
    ).dt.days

    # Exclude negative ages from age summaries.
    df.loc[df["age_days"] < 0, "age_days"] = pd.NA

    # 1. Overall health summary.
    overall = pd.DataFrame([{
        "total_batteries": len(df),
        "valid_current_soh": df["current_soh_pct"].notna().sum(),
        "average_initial_soh_pct": df["initial_soh_pct"].mean(),
        "average_current_soh_pct": df["current_soh_pct"].mean(),
        "average_reported_degradation_pct":
            df["reported_degradation_pct"].mean(),
        "batteries_below_80_soh": (
            df["current_soh_pct"].lt(80).sum()
        ),
        "batteries_below_70_soh": (
            df["current_soh_pct"].lt(70).sum()
        ),
        "retired_batteries": df["retired_date"].notna().sum(),
        "average_age_days": df["age_days"].mean(),
    }])

    overall.to_csv(
        config.TABLES_DIR / "battery_health_overall.csv",
        index=False
    )

    # 2. Health category distribution.
    health_distribution = (
        df.groupby(
            "health_category",
            dropna=False
        )
        .agg(
            battery_count=("battery_id", "nunique"),
            average_current_soh_pct=("current_soh_pct", "mean"),
            average_initial_soh_pct=("initial_soh_pct", "mean"),
            average_age_days=("age_days", "mean"),
        )
        .reset_index()
        .sort_values("battery_count", ascending=False)
    )

    health_distribution.to_csv(
        config.TABLES_DIR / "battery_health_distribution.csv",
        index=False
    )

    # 3. Health by battery pack type.
    health_by_type = (
        df.groupby("pack_type", dropna=False)
        .agg(
            battery_count=("battery_id", "nunique"),
            average_initial_soh_pct=("initial_soh_pct", "mean"),
            average_current_soh_pct=("current_soh_pct", "mean"),
            average_degradation_pct=(
                "reported_degradation_pct", "mean"
            ),
            average_age_days=("age_days", "mean"),
            retired_batteries=("retired_date", "count"),
        )
        .reset_index()
    )

    health_by_type.to_csv(
        config.TABLES_DIR / "battery_health_by_pack_type.csv",
        index=False
    )

    # 4. Health by supplier.
    health_by_supplier = (
        df.groupby("supplier", dropna=False)
        .agg(
            battery_count=("battery_id", "nunique"),
            average_initial_soh_pct=("initial_soh_pct", "mean"),
            average_current_soh_pct=("current_soh_pct", "mean"),
            average_degradation_pct=(
                "reported_degradation_pct", "mean"
            ),
            retired_batteries=("retired_date", "count"),
        )
        .reset_index()
    )

    health_by_supplier.to_csv(
        config.TABLES_DIR / "battery_health_by_supplier.csv",
        index=False
    )

    # 5. Retirement reasons.
    retirement_reasons = (
        df[df["retired_date"].notna()]
        .groupby("retirement_reason", dropna=False)
        .agg(
            retired_battery_count=("battery_id", "nunique"),
            average_current_soh_pct=("current_soh_pct", "mean"),
            average_age_days=("age_days", "mean"),
        )
        .reset_index()
        .sort_values(
            "retired_battery_count",
            ascending=False
        )
    )

    retirement_reasons.to_csv(
        config.TABLES_DIR / "battery_retirement_reasons.csv",
        index=False
    )

    # 6. Data quality checks.
    quality = pd.DataFrame([{
        "total_batteries": len(df),
        "duplicate_battery_ids": (
            df["battery_id"].duplicated().sum()
        ),
        "missing_initial_soh": (
            df["initial_soh_pct"].isna().sum()
        ),
        "missing_current_soh": (
            df["current_soh_pct"].isna().sum()
        ),
        "initial_soh_below_0": (
            df["initial_soh_pct"].lt(0).sum()
        ),
        "initial_soh_above_100": (
            df["initial_soh_pct"].gt(100).sum()
        ),
        "current_soh_below_0": (
            df["current_soh_pct"].lt(0).sum()
        ),
        "current_soh_above_100": (
            df["current_soh_pct"].gt(100).sum()
        ),
        "negative_reported_degradation": (
            df["reported_degradation_pct"].lt(0).sum()
        ),
        "missing_commission_date": (
            df["commission_date"].isna().sum()
        ),
        "retired_before_commission": (
            (
                df["retired_date"].notna()
                & df["commission_date"].notna()
                & (
                    df["retired_date"]
                    < df["commission_date"]
                )
            ).sum()
        ),
    }])

    quality.to_csv(
        config.TABLES_DIR / "battery_health_quality.csv",
        index=False
    )

    print("\nBATTERY MASTER HEALTH SUMMARY")
    print(overall.to_string(index=False))

    print("\nHEALTH CATEGORY DISTRIBUTION")
    print(health_distribution.to_string(index=False))

    print("\nHEALTH BY PACK TYPE")
    print(health_by_type.to_string(index=False))

    print("\nRETIREMENT REASONS")
    print(retirement_reasons.to_string(index=False))

    print("\nBATTERY DATA QUALITY")
    print(quality.to_string(index=False))

    return df


# ---------------------------------------------------------
# 4. SWAP OUTCOMES BY INCOMING BATTERY HEALTH
# ---------------------------------------------------------

def analyze_swap_health(connection):
    """
    Analyze event outcomes by the SOH of the incoming battery.

    Uses event-level soh_in_pct from swap_events.
    Failure rates are descriptive associations, not proof
    that battery health causes a swap failure.
    """

    query = """
        SELECT
            CASE
                WHEN soh_in_pct IS NULL
                    THEN 'Unknown'
                WHEN soh_in_pct < 70
                    THEN 'Below 70%'
                WHEN soh_in_pct < 80
                    THEN '70-79.9%'
                WHEN soh_in_pct < 90
                    THEN '80-89.9%'
                ELSE '90%+'
            END AS incoming_soh_category,

            COUNT(*) AS total_attempts,

            SUM(
                CASE
                    WHEN event_type = 'swap_completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_swaps,

            SUM(
                CASE
                    WHEN event_type IN (
                        'failed_no_charged_battery',
                        'failed_system_error'
                    )
                    THEN 1 ELSE 0
                END
            ) AS failed_attempts,

            SUM(
                CASE
                    WHEN event_type = 'failed_no_charged_battery'
                    THEN 1 ELSE 0
                END
            ) AS no_battery_failures,

            SUM(
                CASE
                    WHEN event_type = 'failed_system_error'
                    THEN 1 ELSE 0
                END
            ) AS system_error_failures,

            SUM(
                CASE
                    WHEN event_type = 'abandoned_queue'
                    THEN 1 ELSE 0
                END
            ) AS abandoned_attempts,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN event_type IN (
                            'failed_no_charged_battery',
                            'failed_system_error'
                        )
                        THEN 1 ELSE 0
                    END
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct,

            ROUND(
                AVG(queue_wait_sec),
                2
            ) AS avg_queue_wait_sec

        FROM swap_events
        GROUP BY incoming_soh_category
        ORDER BY
            CASE incoming_soh_category
                WHEN 'Below 70%' THEN 1
                WHEN '70-79.9%' THEN 2
                WHEN '80-89.9%' THEN 3
                WHEN '90%+' THEN 4
                ELSE 5
            END
    """

    result = connection.execute(query).df()

    result.to_csv(
        config.TABLES_DIR / "swap_outcomes_by_incoming_soh.csv",
        index=False
    )

    print("\nSWAP OUTCOMES BY INCOMING BATTERY SOH")
    print(result.to_string(index=False))

    return result


# ---------------------------------------------------------
# 5. BATTERY USAGE AND EVENT COUNTS
# ---------------------------------------------------------

def analyze_battery_usage(connection):
    """
    Count battery appearances in swap events.

    Incoming battery IDs and outgoing battery IDs represent
    different roles, so they are counted separately.
    """

    query = """
        WITH battery_usage AS (

            SELECT
                battery_in_id AS battery_id,
                COUNT(*) AS incoming_appearances,
                0 AS outgoing_appearances
            FROM swap_events
            WHERE battery_in_id IS NOT NULL
            GROUP BY battery_in_id

            UNION ALL

            SELECT
                battery_out_id AS battery_id,
                0 AS incoming_appearances,
                COUNT(*) AS outgoing_appearances
            FROM swap_events
            WHERE battery_out_id IS NOT NULL
            GROUP BY battery_out_id
        )

        SELECT
            battery_id,
            SUM(incoming_appearances) AS incoming_appearances,
            SUM(outgoing_appearances) AS outgoing_appearances,
            SUM(incoming_appearances + outgoing_appearances)
                AS total_appearances

        FROM battery_usage
        GROUP BY battery_id
        ORDER BY total_appearances DESC
    """

    usage = connection.execute(query).df()

    usage.to_csv(
        config.TABLES_DIR / "battery_usage_counts.csv",
        index=False
    )

    print("\nBATTERY USAGE SUMMARY")
    print(f"Unique batteries appearing in events: {len(usage):,}")

    print("\nTop 10 batteries by event appearances:")
    print(usage.head(10).to_string(index=False))

    return usage


# ---------------------------------------------------------
# 6. MAIN PIPELINE
# ---------------------------------------------------------

def main():

    print("=" * 65)
    print("VOLTRELAY BATTERY HEALTH ANALYSIS")
    print("=" * 65)

    config.TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = connect_database()

    try:
        batteries = load_battery_data()

        print(f"\nLoaded {len(batteries):,} battery records.")

        # Master battery health analysis.
        analyze_battery_health(batteries)

        # Swap outcome analysis by event-level SOH.
        analyze_swap_health(connection)

        # Battery event appearance counts.
        analyze_battery_usage(connection)

    finally:
        connection.close()

    print("\n" + "=" * 65)
    print("BATTERY HEALTH ANALYSIS COMPLETED")
    print("=" * 65)

    print(
        "\nOutput files saved in:",
        config.TABLES_DIR
    )


if __name__ == "__main__":
    main()