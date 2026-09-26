
"""
VoltRelay Energy Analytics
File: src/kpi_analysis.py

Calculates network-level business KPIs from swap events.
"""

import duckdb

from src import config


def connect_database():
    """Connect to the existing DuckDB database."""

    connection = duckdb.connect(
        str(config.PROCESSED_DATA_DIR / "voltrelay.duckdb")
    )

    connection.execute("SET threads = 4")

    return connection


def calculate_monthly_kpis(connection):
    """Calculate monthly swap, revenue, and service KPIs."""

    print("\n" + "=" * 70)
    print("1. MONTHLY NETWORK KPIs")
    print("=" * 70)

    query = """
        SELECT
            DATE_TRUNC('month', event_ts)::DATE AS month,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'swap_completed'
            ) AS completed_swaps,

            COUNT(*) FILTER (
                WHERE event_type IN (
                    'failed_no_charged_battery',
                    'failed_system_error'
                )
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'abandoned_queue'
            ) AS abandoned_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'cancelled_by_rider'
            ) AS cancelled_attempts,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE event_type IN (
                        'failed_no_charged_battery',
                        'failed_system_error'
                    )
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE event_type = 'abandoned_queue'
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS abandonment_rate_pct,

            ROUND(
                SUM(amount_charged_inr) FILTER (
                    WHERE event_type = 'swap_completed'
                ),
                2
            ) AS completed_revenue_inr,

            ROUND(
                AVG(queue_wait_sec),
                2
            ) AS avg_queue_wait_sec,

            MEDIAN(queue_wait_sec)
                AS median_queue_wait_sec

        FROM swap_events

        GROUP BY 1

        ORDER BY 1
    """

    results = connection.execute(query).fetchdf()

    print(results.to_string(index=False))

    output_path = config.TABLES_DIR / "monthly_network_kpis.csv"

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")

    return results


def calculate_city_kpis(connection):
    """Calculate network KPIs by city."""

    print("\n" + "=" * 70)
    print("2. CITY-LEVEL NETWORK KPIs")
    print("=" * 70)

    query = """
        SELECT
            s.city,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE e.event_type = 'swap_completed'
            ) AS completed_swaps,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE e.event_type IN (
                        'failed_no_charged_battery',
                        'failed_system_error'
                    )
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE e.event_type = 'abandoned_queue'
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS abandonment_rate_pct,

            ROUND(
                SUM(e.amount_charged_inr) FILTER (
                    WHERE e.event_type = 'swap_completed'
                ),
                2
            ) AS completed_revenue_inr,

            ROUND(
                AVG(e.queue_wait_sec),
                2
            ) AS avg_queue_wait_sec

        FROM swap_events e

        LEFT JOIN stations s
            ON e.station_id = s.station_id

        GROUP BY s.city

        ORDER BY completed_swaps DESC
    """

    results = connection.execute(query).fetchdf()

    print(results.to_string(index=False))

    output_path = config.TABLES_DIR / "city_network_kpis.csv"

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")

    return results


def calculate_station_kpis(connection):
    """Calculate station-level performance metrics."""

    print("\n" + "=" * 70)
    print("3. STATION-LEVEL PERFORMANCE")
    print("=" * 70)

    query = """
        SELECT
            e.station_id,
            s.city,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE e.event_type = 'swap_completed'
            ) AS completed_swaps,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE e.event_type IN (
                        'failed_no_charged_battery',
                        'failed_system_error'
                    )
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct,

            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE e.event_type = 'abandoned_queue'
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS abandonment_rate_pct,

            ROUND(
                AVG(e.queue_wait_sec),
                2
            ) AS avg_queue_wait_sec,

            ROUND(
                SUM(e.amount_charged_inr) FILTER (
                    WHERE e.event_type = 'swap_completed'
                ),
                2
            ) AS completed_revenue_inr

        FROM swap_events e

        LEFT JOIN stations s
            ON e.station_id = s.station_id

        GROUP BY
            e.station_id,
            s.city

        ORDER BY completed_swaps DESC
    """

    results = connection.execute(query).fetchdf()

    output_path = config.TABLES_DIR / "station_network_kpis.csv"

    results.to_csv(output_path, index=False)

    print(f"Stations analyzed: {len(results):,}")
    print(f"Saved: {output_path}")

    print("\nTop 10 stations by completed swaps:")

    print(
        results.head(10).to_string(index=False)
    )

    return results


def main():
    """Run the initial network KPI analysis."""

    print("\n" + "*" * 70)
    print("VOLTRELAY ENERGY - NETWORK KPI ANALYSIS")
    print("*" * 70)

    config.TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = connect_database()

    try:
        # Register station dimension for city and station joins.
        stations_path = (
            str(config.STATIONS_FILE)
            .replace("\\", "/")
            .replace("'", "''")
        )

        connection.execute(f"""
            CREATE OR REPLACE VIEW stations AS
            SELECT *
            FROM read_csv_auto(
                '{stations_path}',
                header = true
            )
        """)

        calculate_monthly_kpis(connection)
        calculate_city_kpis(connection)
        calculate_station_kpis(connection)

    finally:
        connection.close()

    print("\n" + "*" * 70)
    print("NETWORK KPI ANALYSIS COMPLETED")
    print("*" * 70)


if __name__ == "__main__":
    main()