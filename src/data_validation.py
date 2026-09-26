
"""
VoltRelay Energy
Data Quality Validation Module

Validates large and small datasets for:
- Record counts
- Duplicate identifiers
- Missing values
- Invalid numerical values
- Event and timestamp anomalies
- Reference integrity
"""

import duckdb
import pandas as pd

from src import config

def connect_database():
    """Connect to DuckDB and register all dimension tables."""

    connection = duckdb.connect(
    str(config.PROCESSED_DATA_DIR / "voltrelay.duckdb")
)

    connection.execute("SET threads = 4")

    # Register the six smaller datasets as DuckDB views.
    small_files = {
        "riders": config.RIDERS_FILE,
        "batteries": config.BATTERIES_FILE,
        "support_tickets": config.SUPPORT_TICKETS_FILE,
        "stations": config.STATIONS_FILE,
        "city_context": config.CITY_CONTEXT_FILE,
        "fleet_partners": config.FLEET_PARTNERS_FILE,
    }

    print("\nRegistering small datasets for validation...")

    for table_name, file_path in small_files.items():

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required dataset not found: {file_path}"
            )

        safe_path = (
            str(file_path)
            .replace("\\", "/")
            .replace("'", "''")
        )

        query = f"""
            CREATE OR REPLACE VIEW {table_name} AS
            SELECT *
            FROM read_csv_auto(
                '{safe_path}',
                header = true,
                sample_size = 20000
            )
        """

        connection.execute(query)

        print(f"Registered: {table_name}")

    return connection


def run_query(connection, query):
    """Execute a SQL query and return a DataFrame."""

    return connection.execute(query).fetchdf()


def validate_row_counts(connection):
    """Validate row counts of large datasets."""

    print("\n" + "=" * 70)
    print("1. DATASET ROW COUNT VALIDATION")
    print("=" * 70)

    query = """
        SELECT 'swap_events' AS dataset, COUNT(*) AS row_count
        FROM swap_events

        UNION ALL

        SELECT 'station_hourly_status', COUNT(*)
        FROM station_hourly_status
    """

    results = run_query(connection, query)

    print(results.to_string(index=False))

    output_path = (
        config.TABLES_DIR / "validation_row_counts.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def validate_swap_events(connection):
    """Check swap event quality and anomalies."""

    print("\n" + "=" * 70)
    print("2. SWAP EVENTS DATA QUALITY")
    print("=" * 70)

    query = """
        SELECT
            COUNT(*) AS total_rows,

            COUNT(DISTINCT event_id)
                AS unique_event_ids,

            COUNT(*) - COUNT(DISTINCT event_id)
                AS duplicate_event_ids,

            COUNT(*) FILTER (
                WHERE event_id IS NULL
            ) AS missing_event_ids,

            COUNT(*) FILTER (
                WHERE rider_id IS NULL
            ) AS missing_rider_ids,

            COUNT(*) FILTER (
                WHERE station_id IS NULL
            ) AS missing_station_ids,

            COUNT(*) FILTER (
                WHERE event_ts IS NULL
            ) AS missing_timestamps,

            COUNT(*) FILTER (
                WHERE event_type IS NULL
            ) AS missing_event_types,

            COUNT(*) FILTER (
                WHERE queue_wait_sec < 0
            ) AS negative_queue_waits,

            COUNT(*) FILTER (
                WHERE km_since_last_swap < 0
            ) AS negative_km_readings,

            COUNT(*) FILTER (
                WHERE km_since_last_swap > 300
            ) AS unusually_high_km_readings,

            COUNT(*) FILTER (
                WHERE soc_in_pct < 0
                   OR soc_in_pct > 100
            ) AS invalid_soc_in,

            COUNT(*) FILTER (
                WHERE soc_out_pct < 0
                   OR soc_out_pct > 100
            ) AS invalid_soc_out,

            COUNT(*) FILTER (
                WHERE soh_in_pct < 0
                   OR soh_in_pct > 100
            ) AS invalid_soh_in,

            COUNT(*) FILTER (
                WHERE soh_out_pct < 0
                   OR soh_out_pct > 100
            ) AS invalid_soh_out,

            COUNT(*) FILTER (
                WHERE amount_charged_inr < 0
            ) AS negative_charges,

            COUNT(*) FILTER (
                WHERE discount_inr < 0
            ) AS negative_discounts,

            COUNT(*) FILTER (
                WHERE event_type = 'swap_completed'
                  AND battery_out_id IS NULL
            ) AS completed_without_output_battery

        FROM swap_events
    """

    results = run_query(connection, query)

    print(results.T.to_string(header=False))

    output_path = (
        config.TABLES_DIR / "swap_events_quality.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def validate_event_types(connection):
    """Inspect event types and event volumes."""

    print("\n" + "=" * 70)
    print("3. SWAP EVENT TYPE DISTRIBUTION")
    print("=" * 70)

    query = """
        SELECT
            event_type,
            COUNT(*) AS event_count,
            ROUND(
                100.0 * COUNT(*) /
                SUM(COUNT(*)) OVER (),
                2
            ) AS percentage
        FROM swap_events
        GROUP BY event_type
        ORDER BY event_count DESC
    """

    results = run_query(connection, query)

    print(results.to_string(index=False))

    output_path = (
        config.TABLES_DIR / "event_type_distribution.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def validate_timestamp_range(connection):
    """Check the timestamp range and daily event volumes."""

    print("\n" + "=" * 70)
    print("4. TIMESTAMP RANGE VALIDATION")
    print("=" * 70)

    query = """
        SELECT
            MIN(event_ts) AS earliest_event,
            MAX(event_ts) AS latest_event,
            COUNT(*) FILTER (
                WHERE event_ts < TIMESTAMP '2024-01-01'
            ) AS before_expected_period,
            COUNT(*) FILTER (
                WHERE event_ts >= TIMESTAMP '2025-07-01'
            ) AS after_expected_period
        FROM swap_events
    """

    results = run_query(connection, query)

    print(results.to_string(index=False))

    output_path = (
        config.TABLES_DIR / "timestamp_validation.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def validate_station_telemetry(connection):
    """Check station telemetry data quality."""

    print("\n" + "=" * 70)
    print("5. STATION TELEMETRY QUALITY")
    print("=" * 70)

    query = """
        SELECT
            COUNT(*) AS total_rows,

            COUNT(*) - COUNT(
                DISTINCT station_id || '_' ||
                CAST(hour_start AS VARCHAR)
            ) AS duplicate_station_hours,

            COUNT(*) FILTER (
                WHERE station_id IS NULL
            ) AS missing_station_ids,

            COUNT(*) FILTER (
                WHERE hour_start IS NULL
            ) AS missing_timestamps,

            COUNT(*) FILTER (
                WHERE outage_minutes < 0
                   OR outage_minutes > 60
            ) AS invalid_outage_minutes,

            COUNT(*) FILTER (
                WHERE chargers_online < 0
            ) AS negative_chargers_online,

            COUNT(*) FILTER (
                WHERE packs_quarantined < 0
            ) AS negative_quarantined_packs,

            COUNT(*) FILTER (
                WHERE grid_kwh < 0
            ) AS negative_grid_energy,

            COUNT(*) FILTER (
                WHERE cabinet_temp_c < ambient_temp_c
            ) AS cabinet_cooler_than_ambient

        FROM station_hourly_status
    """

    results = run_query(connection, query)

    print(results.T.to_string(header=False))

    output_path = (
        config.TABLES_DIR / "station_telemetry_quality.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def validate_reference_integrity(connection):
    """Check whether event references exist in dimension tables."""

    print("\n" + "=" * 70)
    print("6. REFERENCE INTEGRITY")
    print("=" * 70)

    query = """
        SELECT
            'Unknown rider IDs' AS check_name,
            COUNT(*) AS issue_count
        FROM swap_events e
        LEFT JOIN riders r
            ON e.rider_id = r.rider_id
        WHERE e.rider_id IS NOT NULL
          AND r.rider_id IS NULL

        UNION ALL

        SELECT
            'Unknown station IDs',
            COUNT(*)
        FROM swap_events e
        LEFT JOIN stations s
            ON e.station_id = s.station_id
        WHERE e.station_id IS NOT NULL
          AND s.station_id IS NULL

        UNION ALL

        SELECT
            'Unknown incoming battery IDs',
            COUNT(*)
        FROM swap_events e
        LEFT JOIN batteries b
            ON e.battery_in_id = b.battery_id
        WHERE e.battery_in_id IS NOT NULL
          AND b.battery_id IS NULL

        UNION ALL

        SELECT
            'Unknown outgoing battery IDs',
            COUNT(*)
        FROM swap_events e
        LEFT JOIN batteries b
            ON e.battery_out_id = b.battery_id
        WHERE e.battery_out_id IS NOT NULL
          AND b.battery_id IS NULL
    """

    results = run_query(connection, query)

    print(results.to_string(index=False))

    output_path = (
        config.TABLES_DIR / "reference_integrity.csv"
    )

    results.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")


def main():
    """Run the complete validation pipeline."""

    print("\n" + "*" * 70)
    print("VOLTRELAY ENERGY - DATA VALIDATION")
    print("*" * 70)

    config.TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = connect_database()

    try:
        validate_row_counts(connection)
        validate_swap_events(connection)
        validate_event_types(connection)
        validate_timestamp_range(connection)
        validate_station_telemetry(connection)
        validate_reference_integrity(connection)

    finally:
        connection.close()

    print("\n" + "*" * 70)
    print("DATA VALIDATION COMPLETED")
    print("*" * 70)


if __name__ == "__main__":
    main()