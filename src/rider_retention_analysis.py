
"""
VoltRelay Rider Retention and Churn Analysis
---------------------------------------------
Analyzes rider engagement, repeat usage, monthly retention,
inactivity-based churn, and rider revenue.

Run from the project root:
    python -m src.rider_retention_analysis

Data sources:
    data/raw/riders.csv
    data/processed/voltrelay.duckdb

Churn definition:
    A rider with at least one completed swap is classified
    as inactive if their last completed swap occurred before
    the 30-day inactivity cutoff.

The cutoff is based on the maximum event timestamp in the
dataset, not today's date.

This is an inactivity proxy, not proof of permanent churn.
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
# 2. REGISTER RIDER MASTER DATA
# ---------------------------------------------------------

def register_rider_data(connection):
    """Register the rider master CSV as a DuckDB view."""

    rider_path = str(config.RIDERS_FILE).replace("\\", "/")

    connection.execute(
        f"""
        CREATE OR REPLACE VIEW riders_ref AS
        SELECT *
        FROM read_csv_auto(
            '{rider_path}',
            header = true,
            sample_size = 20000
        )
        """
    )

    columns = connection.execute(
        "DESCRIBE riders_ref"
    ).df()

    print("\nRIDER MASTER DATA COLUMNS")
    print(columns.to_string(index=False))


# ---------------------------------------------------------
# 3. GET DATASET ANALYSIS END DATE
# ---------------------------------------------------------

def get_analysis_end_date(connection):
    """
    Get the maximum event timestamp from the complete
    swap_events dataset.

    This includes failed, abandoned, cancelled, and
    completed events.
    """

    result = connection.execute(
        """
        SELECT MAX(CAST(event_ts AS TIMESTAMP)) AS max_event_ts
        FROM swap_events
        """
    ).fetchone()

    if result is None or result[0] is None:
        raise ValueError(
            "Cannot calculate analysis end date: "
            "swap_events contains no valid timestamps."
        )

    analysis_end = pd.Timestamp(result[0])

    # Use the calendar date of the final recorded event.
    analysis_end = analysis_end.normalize()

    print(f"\nDataset analysis end date: {analysis_end.date()}")

    return analysis_end


# ---------------------------------------------------------
# 4. RIDER ACTIVITY METRICS
# ---------------------------------------------------------

def analyze_rider_activity(connection):
    """
    Calculate rider-level usage, completed swaps, revenue,
    failures, abandoned attempts, and last activity date.
    """

    query = """
        WITH rider_activity AS (

            SELECT
                rider_id,

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
                        WHEN event_type = 'abandoned_queue'
                        THEN 1 ELSE 0
                    END
                ) AS abandoned_attempts,

                SUM(
                    CASE
                        WHEN event_type = 'cancelled_by_rider'
                        THEN 1 ELSE 0
                    END
                ) AS cancelled_attempts,

                SUM(
                    CASE
                        WHEN event_type = 'swap_completed'
                        THEN COALESCE(amount_charged_inr, 0)
                        ELSE 0
                    END
                ) AS completed_revenue_inr,

                MIN(
                    CASE
                        WHEN event_type = 'swap_completed'
                        THEN CAST(event_ts AS DATE)
                    END
                ) AS first_completed_swap_date,

                MAX(
                    CASE
                        WHEN event_type = 'swap_completed'
                        THEN CAST(event_ts AS DATE)
                    END
                ) AS last_completed_swap_date,

                COUNT(
                    DISTINCT CASE
                        WHEN event_type = 'swap_completed'
                        THEN CAST(event_ts AS DATE)
                    END
                ) AS active_days,

                COUNT(
                    DISTINCT CASE
                        WHEN event_type = 'swap_completed'
                        THEN DATE_TRUNC('month', event_ts)
                    END
                ) AS active_months

            FROM swap_events

            GROUP BY rider_id
        )

        SELECT *
        FROM rider_activity
    """

    activity = connection.execute(query).df()

    date_columns = [
        "first_completed_swap_date",
        "last_completed_swap_date",
    ]

    for column in date_columns:
        activity[column] = pd.to_datetime(
            activity[column],
            errors="coerce"
        )

    numeric_columns = [
        "total_attempts",
        "completed_swaps",
        "failed_attempts",
        "abandoned_attempts",
        "cancelled_attempts",
        "completed_revenue_inr",
        "active_days",
        "active_months",
    ]

    for column in numeric_columns:
        activity[column] = pd.to_numeric(
            activity[column],
            errors="coerce"
        ).fillna(0)

    activity.to_csv(
        config.TABLES_DIR / "rider_activity_metrics.csv",
        index=False
    )

    print("\nRIDER ACTIVITY SUMMARY")

    print(f"Riders with recorded events: {len(activity):,}")

    print(
        "Riders with completed swaps:",
        f"{(activity['completed_swaps'] > 0).sum():,}"
    )

    print(
        "Riders without completed swaps:",
        f"{(activity['completed_swaps'] == 0).sum():,}"
    )

    print(
        "Total completed swaps:",
        f"{activity['completed_swaps'].sum():,.0f}"
    )

    print(
        "Total completed revenue:",
        f"₹{activity['completed_revenue_inr'].sum():,.2f}"
    )

    print("\nTop 10 riders by completed swaps:")

    print(
        activity.sort_values(
            "completed_swaps",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )

    return activity


# ---------------------------------------------------------
# 5. REPEAT RIDER AND ENGAGEMENT SEGMENTATION
# ---------------------------------------------------------

def analyze_rider_segments(activity):
    """Classify riders based on completed swap frequency."""

    df = activity.copy()

    conditions = [
        df["completed_swaps"].eq(0),
        df["completed_swaps"].eq(1),
        df["completed_swaps"].between(2, 5),
        df["completed_swaps"].between(6, 20),
        df["completed_swaps"].gt(20),
    ]

    labels = [
        "No Completed Swaps",
        "One-Time Rider",
        "Occasional Rider (2-5)",
        "Regular Rider (6-20)",
        "Frequent Rider (21+)",
    ]

    df["rider_segment"] = "Unknown"

    for condition, label in zip(conditions, labels):
        df.loc[condition, "rider_segment"] = label

    segment_summary = (
        df.groupby(
            "rider_segment",
            dropna=False
        )
        .agg(
            rider_count=("rider_id", "nunique"),
            completed_swaps=("completed_swaps", "sum"),
            average_completed_swaps=("completed_swaps", "mean"),
            total_revenue_inr=("completed_revenue_inr", "sum"),
            average_revenue_inr=("completed_revenue_inr", "mean"),
        )
        .reset_index()
    )

    total_riders = segment_summary["rider_count"].sum()

    segment_summary["rider_share_pct"] = (
        100 * segment_summary["rider_count"]
        / max(total_riders, 1)
    ).round(2)

    segment_summary.to_csv(
        config.TABLES_DIR / "rider_segment_summary.csv",
        index=False
    )

    df.to_csv(
        config.TABLES_DIR / "rider_segments.csv",
        index=False
    )

    print("\nRIDER SEGMENT SUMMARY")

    print(
        segment_summary.to_string(
            index=False,
            formatters={
                "rider_count": "{:,.0f}".format,
                "completed_swaps": "{:,.0f}".format,
                "average_completed_swaps": "{:.2f}".format,
                "total_revenue_inr": "₹{:,.2f}".format,
                "average_revenue_inr": "₹{:,.2f}".format,
                "rider_share_pct": "{:.2f}%".format,
            }
        )
    )

    return df, segment_summary


# ---------------------------------------------------------
# 6. MONTHLY ACTIVE RIDERS
# ---------------------------------------------------------

def analyze_monthly_active_riders(connection):
    """
    Calculate monthly active riders, completed swaps,
    and completed swap revenue.

    Monthly active riders are distinct riders with at
    least one completed swap in that calendar month.
    """

    query = """
        SELECT
            DATE_TRUNC('month', event_ts)::DATE AS month,

            COUNT(
                DISTINCT CASE
                    WHEN event_type = 'swap_completed'
                    THEN rider_id
                END
            ) AS monthly_active_riders,

            SUM(
                CASE
                    WHEN event_type = 'swap_completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_swaps,

            SUM(
                CASE
                    WHEN event_type = 'swap_completed'
                    THEN COALESCE(amount_charged_inr, 0)
                    ELSE 0
                END
            ) AS completed_revenue_inr

        FROM swap_events

        GROUP BY DATE_TRUNC('month', event_ts)

        ORDER BY month
    """

    monthly = connection.execute(query).df()

    monthly["month"] = pd.to_datetime(
        monthly["month"],
        errors="coerce"
    )

    monthly["active_rider_change"] = (
        monthly["monthly_active_riders"].diff()
    )

    monthly["active_rider_growth_pct"] = (
        monthly["monthly_active_riders"]
        .pct_change(fill_method=None)
        .mul(100)
        .round(2)
    )

    monthly.to_csv(
        config.TABLES_DIR / "monthly_active_riders.csv",
        index=False
    )

    print("\nMONTHLY ACTIVE RIDERS")

    print(
        monthly.to_string(
            index=False,
            formatters={
                "monthly_active_riders": "{:,.0f}".format,
                "completed_swaps": "{:,.0f}".format,
                "completed_revenue_inr": "₹{:,.2f}".format,
                "active_rider_change": "{:,.0f}".format,
                "active_rider_growth_pct": "{:.2f}%".format,
            }
        )
    )

    return monthly


# ---------------------------------------------------------
# 7. MONTHLY COHORT RETENTION
# ---------------------------------------------------------

def analyze_cohort_retention(connection):
    """
    Build a monthly cohort retention table.

    Cohort month:
        Month of the rider's first completed swap.

    Retention:
        Percentage of cohort riders with at least one
        completed swap in each subsequent month.

    Cohort month 0 represents the initial activity month.
    """

    query = """
        WITH completed_events AS (

            SELECT DISTINCT
                rider_id,
                DATE_TRUNC('month', event_ts)::DATE
                    AS activity_month

            FROM swap_events

            WHERE event_type = 'swap_completed'
              AND rider_id IS NOT NULL
        ),

        first_activity AS (

            SELECT
                rider_id,
                MIN(activity_month) AS cohort_month

            FROM completed_events

            GROUP BY rider_id
        ),

        cohort_activity AS (

            SELECT DISTINCT
                f.rider_id,
                f.cohort_month,
                e.activity_month,

                DATE_DIFF(
                    'month',
                    f.cohort_month,
                    e.activity_month
                ) AS month_number

            FROM first_activity f

            INNER JOIN completed_events e
                ON f.rider_id = e.rider_id

            WHERE e.activity_month >= f.cohort_month
        ),

        cohort_sizes AS (

            SELECT
                cohort_month,
                COUNT(DISTINCT rider_id) AS cohort_size

            FROM first_activity

            GROUP BY cohort_month
        )

        SELECT
            a.cohort_month,
            a.month_number,
            s.cohort_size,

            COUNT(DISTINCT a.rider_id) AS retained_riders,

            ROUND(
                100.0 * COUNT(DISTINCT a.rider_id)
                / NULLIF(s.cohort_size, 0),
                2
            ) AS retention_rate_pct

        FROM cohort_activity a

        INNER JOIN cohort_sizes s
            ON a.cohort_month = s.cohort_month

        GROUP BY
            a.cohort_month,
            a.month_number,
            s.cohort_size

        ORDER BY
            a.cohort_month,
            a.month_number
    """

    cohort = connection.execute(query).df()

    cohort.to_csv(
        config.TABLES_DIR / "rider_cohort_retention.csv",
        index=False
    )

    print("\nCOHORT RETENTION SUMMARY")

    print(
        f"Available cohort-month observations: {len(cohort):,}"
    )

    print("\nFirst 20 cohort observations:")

    print(
        cohort.head(20).to_string(
            index=False,
            formatters={
                "cohort_size": "{:,.0f}".format,
                "retained_riders": "{:,.0f}".format,
                "retention_rate_pct": "{:.2f}%".format,
            }
        )
    )

    return cohort


# ---------------------------------------------------------
# 8. INACTIVITY-BASED CHURN
# ---------------------------------------------------------

def analyze_rider_churn(activity, analysis_end):
    """
    Identify riders inactive during the final 30 days
    of the observed dataset.

    The end date is the maximum event timestamp in the
    complete dataset.

    The inactivity cutoff is exclusive:
    a last completed swap strictly before the cutoff
    is classified as inactive.
    """

    df = activity.copy()

    # Start of the final 30-day observation window.
    churn_cutoff = analysis_end - pd.Timedelta(days=30)

    df["days_since_last_completed_swap"] = (
        analysis_end - df["last_completed_swap_date"]
    ).dt.days

    df["churn_status"] = "No Completed Swap"

    has_completed = (
        df["last_completed_swap_date"].notna()
    )

    # Riders whose last completed swap is within
    # the final 30-day window.
    df.loc[
        has_completed
        & (
            df["last_completed_swap_date"]
            >= churn_cutoff
        ),
        "churn_status"
    ] = "Active in Final 30 Days"

    # Riders whose last completed swap occurred
    # before the final 30-day window.
    df.loc[
        has_completed
        & (
            df["last_completed_swap_date"]
            < churn_cutoff
        ),
        "churn_status"
    ] = "Inactive in Final 30 Days"

    summary = (
        df.groupby(
            "churn_status",
            dropna=False
        )
        .agg(
            rider_count=("rider_id", "nunique"),
            completed_swaps=("completed_swaps", "sum"),
            total_revenue_inr=("completed_revenue_inr", "sum"),
            average_completed_swaps=("completed_swaps", "mean"),
            average_days_since_last_swap=(
                "days_since_last_completed_swap",
                "mean"
            ),
        )
        .reset_index()
    )

    # Churn rate denominator includes only riders
    # with at least one completed swap.
    eligible_riders = df[has_completed]

    churned_riders = eligible_riders[
        eligible_riders["churn_status"]
        == "Inactive in Final 30 Days"
    ]

    eligible_count = len(eligible_riders)

    churn_rate = (
        100 * len(churned_riders)
        / max(eligible_count, 1)
    )

    summary.to_csv(
        config.TABLES_DIR / "rider_churn_summary.csv",
        index=False
    )

    df.to_csv(
        config.TABLES_DIR / "rider_churn_details.csv",
        index=False
    )

    print("\nINACTIVITY-BASED CHURN SUMMARY")

    print(f"Analysis end date: {analysis_end.date()}")

    print(f"30-day inactivity cutoff: {churn_cutoff.date()}")

    print(f"Riders with completed swaps: {eligible_count:,}")

    print(
        "Riders inactive in final 30 days:",
        f"{len(churned_riders):,}"
    )

    print(
        "Inactivity rate among riders with completed swaps:",
        f"{churn_rate:.2f}%"
    )

    print("\nChurn status breakdown:")

    print(
        summary.to_string(
            index=False,
            formatters={
                "rider_count": "{:,.0f}".format,
                "completed_swaps": "{:,.0f}".format,
                "total_revenue_inr": "₹{:,.2f}".format,
                "average_completed_swaps": "{:.2f}".format,
                "average_days_since_last_swap": "{:.2f}".format,
            }
        )
    )

    return df, summary


# ---------------------------------------------------------
# 9. RIDER MASTER DATA QUALITY / COVERAGE
# ---------------------------------------------------------

def analyze_rider_master_coverage(connection, activity):
    """
    Compare rider IDs in the master data with IDs appearing
    in swap events.
    """

    master_count = connection.execute(
        """
        SELECT
            COUNT(*) AS total_master_rows,
            COUNT(DISTINCT rider_id) AS unique_master_riders
        FROM riders_ref
        """
    ).df()

    event_riders = set(
        activity["rider_id"].dropna()
    )

    master_riders = connection.execute(
        """
        SELECT DISTINCT rider_id
        FROM riders_ref
        WHERE rider_id IS NOT NULL
        """
    ).df()

    master_ids = set(
        master_riders["rider_id"].dropna()
    )

    coverage = pd.DataFrame([{
        "master_rows": int(
            master_count.iloc[0]["total_master_rows"]
        ),
        "unique_master_riders": len(master_ids),
        "unique_event_riders": len(event_riders),
        "event_riders_missing_from_master": len(
            event_riders - master_ids
        ),
        "master_riders_without_events": len(
            master_ids - event_riders
        ),
    }])

    coverage.to_csv(
        config.TABLES_DIR / "rider_master_coverage.csv",
        index=False
    )

    print("\nRIDER MASTER COVERAGE")

    print(
        coverage.to_string(
            index=False,
            formatters={
                column: "{:,.0f}".format
                for column in coverage.columns
            }
        )
    )

    return coverage


# ---------------------------------------------------------
# 10. MAIN PIPELINE
# ---------------------------------------------------------

def main():

    print("=" * 65)
    print("VOLTRELAY RIDER RETENTION AND CHURN ANALYSIS")
    print("=" * 65)

    config.TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = connect_database()

    try:
        # Register rider master data.
        register_rider_data(connection)

        # Get the true end date from all event records.
        analysis_end = get_analysis_end_date(connection)

        # Rider-level engagement and revenue.
        activity = analyze_rider_activity(connection)

        # Rider frequency segmentation.
        analyze_rider_segments(activity)

        # Monthly active riders.
        analyze_monthly_active_riders(connection)

        # Monthly cohort retention.
        analyze_cohort_retention(connection)

        # Inactivity-based churn.
        analyze_rider_churn(
            activity,
            analysis_end
        )

        # Compare master data with event coverage.
        analyze_rider_master_coverage(
            connection,
            activity
        )

    finally:
        connection.close()

    print("\n" + "=" * 65)
    print("RIDER RETENTION ANALYSIS COMPLETED")
    print("=" * 65)

    print("\nOutput files saved in:")
    print(config.TABLES_DIR)


if __name__ == "__main__":
    main()