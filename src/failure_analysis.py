
import duckdb

from src import config


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def connect_database():

    db_path = config.PROCESSED_DATA_DIR / "voltrelay.duckdb"

    con = duckdb.connect(str(db_path))
    con.execute("SET threads = 4")

    # Register station reference data for city-level analysis.
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW stations_ref AS
        SELECT *
        FROM read_csv_auto(
            '{config.STATIONS_FILE.as_posix()}',
            header = true
        )
    """)

    return con


# --------------------------------------------------
# COMMON FAILURE DEFINITIONS
# --------------------------------------------------

# Operational failures:
# - failed_no_charged_battery
# - failed_system_error
#
# Other unsuccessful outcomes, such as abandoned or
# cancelled attempts, are tracked separately.

FAILURE_CONDITION = """
    event_type IN (
        'failed_no_charged_battery',
        'failed_system_error'
    )
"""


# --------------------------------------------------
# 1. FAILURE ANALYSIS BY MONTH AND EVENT TYPE
# --------------------------------------------------

def analyze_monthly_failures(con):

    print("\n1. MONTHLY FAILURE ANALYSIS")

    query = f"""
        SELECT
            DATE_TRUNC('month', event_ts)::DATE AS month,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE {FAILURE_CONDITION}
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_charged_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'abandoned_queue'
            ) AS abandoned_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'cancelled_by_rider'
            ) AS cancelled_attempts,

            ROUND(
                100.0 *
                COUNT(*) FILTER (
                    WHERE {FAILURE_CONDITION}
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct

        FROM swap_events

        GROUP BY 1
        ORDER BY 1
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_analysis_monthly.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")

    return df


# --------------------------------------------------
# 2. FAILURE ANALYSIS BY FIRMWARE
# --------------------------------------------------

def analyze_firmware_failures(con):

    print("\n2. FAILURE ANALYSIS BY FIRMWARE")

    query = f"""
        SELECT
            COALESCE(
                NULLIF(TRIM(station_firmware), ''),
                'Unknown'
            ) AS firmware,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE {FAILURE_CONDITION}
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_charged_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            ROUND(
                100.0 *
                COUNT(*) FILTER (
                    WHERE {FAILURE_CONDITION}
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct

        FROM swap_events

        GROUP BY 1
        ORDER BY failure_rate_pct DESC
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_analysis_firmware.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")

    return df


# --------------------------------------------------
# 3. FAILURE ANALYSIS BY CITY
# --------------------------------------------------

def analyze_city_failures(con):

    print("\n3. FAILURE ANALYSIS BY CITY")

    query = f"""
        SELECT
            COALESCE(s.city, 'Unknown') AS city,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE {FAILURE_CONDITION}
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_charged_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'abandoned_queue'
            ) AS abandoned_attempts,

            ROUND(
                100.0 *
                COUNT(*) FILTER (
                    WHERE {FAILURE_CONDITION}
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct

        FROM swap_events e

        LEFT JOIN stations_ref s
            ON e.station_id = s.station_id

        GROUP BY 1
        ORDER BY failure_rate_pct DESC
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_analysis_city.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")

    return df


# --------------------------------------------------
# 4. FAILURE ANALYSIS BY STATION
# --------------------------------------------------

def analyze_station_failures(con):

    print("\n4. STATION FAILURE ANALYSIS")

    query = f"""
        SELECT
            e.station_id,
            COALESCE(s.city, 'Unknown') AS city,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE {FAILURE_CONDITION}
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_charged_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'abandoned_queue'
            ) AS abandoned_attempts,

            ROUND(
                100.0 *
                COUNT(*) FILTER (
                    WHERE {FAILURE_CONDITION}
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct

        FROM swap_events e

        LEFT JOIN stations_ref s
            ON e.station_id = s.station_id

        GROUP BY 1, 2

        ORDER BY failure_rate_pct DESC
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_analysis_station.csv"
    df.to_csv(output, index=False)

    print("\nTop 10 stations by failure rate:")
    print(df.head(10).to_string(index=False))

    print(f"Saved: {output}")

    return df


# --------------------------------------------------
# 5. FAILURE ANALYSIS BY SYNC MODE
# --------------------------------------------------

def analyze_sync_mode_failures(con):

    print("\n5. FAILURE ANALYSIS BY SYNC MODE")

    query = f"""
        SELECT
            COALESCE(
                NULLIF(TRIM(sync_mode), ''),
                'Unknown'
            ) AS sync_mode,

            COUNT(*) AS total_attempts,

            COUNT(*) FILTER (
                WHERE {FAILURE_CONDITION}
            ) AS failed_attempts,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_no_charged_battery'
            ) AS no_charged_battery_failures,

            COUNT(*) FILTER (
                WHERE event_type = 'failed_system_error'
            ) AS system_error_failures,

            ROUND(
                100.0 *
                COUNT(*) FILTER (
                    WHERE {FAILURE_CONDITION}
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS failure_rate_pct

        FROM swap_events

        GROUP BY 1
        ORDER BY failure_rate_pct DESC
    """

    df = con.execute(query).fetchdf()

    output = config.TABLES_DIR / "failure_analysis_sync_mode.csv"
    df.to_csv(output, index=False)

    print(df.to_string(index=False))
    print(f"Saved: {output}")

    return df


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 70)
    print("VOLTRELAY - FAILURE PATTERN ANALYSIS")
    print("=" * 70)

    con = connect_database()

    try:

        config.TABLES_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        analyze_monthly_failures(con)
        analyze_firmware_failures(con)
        analyze_city_failures(con)
        analyze_station_failures(con)
        analyze_sync_mode_failures(con)

    finally:
        con.close()

    print("\n" + "=" * 70)
    print("FAILURE ANALYSIS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()