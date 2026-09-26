
import duckdb

from src import config


def connect_database():

    db_path = config.PROCESSED_DATA_DIR / "voltrelay.duckdb"

    con = duckdb.connect(str(db_path))
    con.execute("SET threads = 4")

    return con


def analyze_telemetry_failures(con):

    print("\n1. AGGREGATING SWAP EVENTS BY STATION-HOUR")

    query = """
        CREATE OR REPLACE TEMP TABLE station_hour_swaps AS
        SELECT
            station_id,
            DATE_TRUNC('hour', event_ts) AS hour_start,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE event_type IN (
                    'failed_no_charged_battery',
                    'failed_system_error'
                )
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'swap_completed'
            ) AS completed_swaps,

            COUNT(*) FILTER (
                WHERE event_type = 'abandoned_queue'
            ) AS abandoned_attempts

        FROM swap_events

        GROUP BY
            station_id,
            DATE_TRUNC('hour', event_ts)
    """

    con.execute(query)

    print("Station-hour swap aggregation completed.")

    print("\n2. JOINING WITH STATION TELEMETRY")

    # Match each station-hour to its corresponding telemetry hour.
    # Use an exact hour match to avoid duplicating event records.

    query = """
        CREATE OR REPLACE TEMP TABLE station_hour_analysis AS
        SELECT
            s.station_id,
            s.hour_start,

            s.total_attempts,
            s.failed_attempts,
            s.no_battery_failures,
            s.system_error_failures,
            s.completed_swaps,
            s.abandoned_attempts,

            t.charged_2w_avg,
            t.charged_2w_min,
            t.charged_3w_min,
            t.packs_charging,
            t.packs_quarantined,
            t.chargers_online,
            t.ambient_temp_c,
            t.cabinet_temp_c,
            t.avg_charge_minutes,
            t.outage_minutes,
            t.grid_kwh,
            t.telemetry_status,

            CASE
                WHEN t.station_id IS NULL THEN 0
                ELSE 1
            END AS telemetry_matched

        FROM station_hour_swaps s

        LEFT JOIN station_hourly_status t
            ON s.station_id = t.station_id
            AND s.hour_start = t.hour_start
    """

    con.execute(query)

    # Confirm that the join has not multiplied event counts.
    validation = con.execute("""
        SELECT
            SUM(total_attempts) AS total_attempts,
            SUM(failed_attempts) AS failed_attempts,
            COUNT(*) AS station_hour_rows,
            SUM(telemetry_matched) AS matched_station_hours,
            ROUND(
                100.0 * SUM(telemetry_matched) /
                NULLIF(COUNT(*), 0),
                2
            ) AS telemetry_match_pct
        FROM station_hour_analysis
    """).fetchdf()

    print("\nTelemetry join validation:")
    print(validation.to_string(index=False))

    output = config.TABLES_DIR / "telemetry_join_validation.csv"
    validation.to_csv(output, index=False)

    return validation


def analyze_inventory_conditions(con):

    print("\n3. FAILURE RATE BY BATTERY INVENTORY")

    query = """
        SELECT
            CASE
                WHEN charged_2w_avg IS NULL
                    THEN 'Unknown'
                WHEN charged_2w_avg < 3
                    THEN 'Low: below 3'
                WHEN charged_2w_avg < 6
                    THEN 'Moderate: 3 to below 6'
                ELSE 'High: 6 or more'
            END AS inventory_group,

            COUNT(*) AS station_hours,
            SUM(total_attempts) AS total_attempts,
            SUM(failed_attempts) AS failed_attempts,

            ROUND(
                100.0 * SUM(failed_attempts) /
                NULLIF(SUM(total_attempts), 0),
                2
            ) AS failure_rate_pct,

            SUM(no_battery_failures) AS no_battery_failures,
            SUM(completed_swaps) AS completed_swaps

        FROM station_hour_analysis

        GROUP BY 1
        ORDER BY 1
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_by_inventory.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")


def analyze_outage_conditions(con):

    print("\n4. FAILURE RATE BY OUTAGE CONDITIONS")

    query = """
        SELECT
            CASE
                WHEN outage_minutes IS NULL
                    THEN 'Unknown'
                WHEN outage_minutes = 0
                    THEN 'No outage'
                WHEN outage_minutes <= 15
                    THEN '1-15 outage minutes'
                WHEN outage_minutes <= 30
                    THEN '16-30 outage minutes'
                ELSE 'More than 30 outage minutes'
            END AS outage_group,

            COUNT(*) AS station_hours,
            SUM(total_attempts) AS total_attempts,
            SUM(failed_attempts) AS failed_attempts,

            ROUND(
                100.0 * SUM(failed_attempts) /
                NULLIF(SUM(total_attempts), 0),
                2
            ) AS failure_rate_pct,

            SUM(system_error_failures) AS system_error_failures,
            SUM(no_battery_failures) AS no_battery_failures

        FROM station_hour_analysis

        GROUP BY 1
        ORDER BY 1
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_by_outage.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")


def analyze_quarantine_conditions(con):

    print("\n5. FAILURE RATE BY QUARANTINED BATTERY PACKS")

    query = """
        SELECT
            CASE
                WHEN packs_quarantined IS NULL
                    THEN 'Unknown'
                WHEN packs_quarantined = 0
                    THEN 'No quarantined packs'
                WHEN packs_quarantined <= 2
                    THEN '1-2 quarantined packs'
                ELSE 'More than 2 quarantined packs'
            END AS quarantine_group,

            COUNT(*) AS station_hours,
            SUM(total_attempts) AS total_attempts,
            SUM(failed_attempts) AS failed_attempts,

            ROUND(
                100.0 * SUM(failed_attempts) /
                NULLIF(SUM(total_attempts), 0),
                2
            ) AS failure_rate_pct,

            SUM(no_battery_failures) AS no_battery_failures

        FROM station_hour_analysis

        GROUP BY 1
        ORDER BY 1
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_by_quarantine.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")


def analyze_temperature_conditions(con):

    print("\n6. FAILURE RATE BY AMBIENT TEMPERATURE")

    query = """
        SELECT
            CASE
                WHEN ambient_temp_c IS NULL
                    THEN 'Unknown'
                WHEN ambient_temp_c < 20
                    THEN 'Below 20 C'
                WHEN ambient_temp_c < 30
                    THEN '20-29.9 C'
                WHEN ambient_temp_c < 40
                    THEN '30-39.9 C'
                ELSE '40 C or above'
            END AS temperature_group,

            COUNT(*) AS station_hours,
            SUM(total_attempts) AS total_attempts,
            SUM(failed_attempts) AS failed_attempts,

            ROUND(
                100.0 * SUM(failed_attempts) /
                NULLIF(SUM(total_attempts), 0),
                2
            ) AS failure_rate_pct,

            SUM(system_error_failures) AS system_error_failures,
            SUM(no_battery_failures) AS no_battery_failures

        FROM station_hour_analysis

        GROUP BY 1
        ORDER BY 1
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_by_temperature.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")


def main():

    print("\n" + "=" * 70)
    print("VOLTRELAY - TELEMETRY FAILURE ANALYSIS")
    print("=" * 70)

    config.TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    con = connect_database()

    try:
        analyze_telemetry_failures(con)
        analyze_inventory_conditions(con)
        analyze_outage_conditions(con)
        analyze_quarantine_conditions(con)
        analyze_temperature_conditions(con)

    finally:
        con.close()

    print("\n" + "=" * 70)
    print("TELEMETRY FAILURE ANALYSIS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()