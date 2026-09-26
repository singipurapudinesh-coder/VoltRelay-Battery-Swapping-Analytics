
import duckdb

from src import config


def main():

    db_path = config.PROCESSED_DATA_DIR / "voltrelay.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)

    try:
        # Check whether station reference IDs are unique.
        con.execute(f"""
            CREATE OR REPLACE TEMP VIEW stations_ref AS
            SELECT *
            FROM read_csv_auto(
                '{config.STATIONS_FILE.as_posix()}',
                header = true
            )
        """)

        print("\n1. STATION REFERENCE DUPLICATES")

        print(con.execute("""
            SELECT
                station_id,
                COUNT(*) AS reference_rows
            FROM stations_ref
            GROUP BY station_id
            HAVING COUNT(*) > 1
            ORDER BY reference_rows DESC
        """).fetchdf().to_string(index=False))

        # Aggregate raw swap events without any join.
        print("\n2. RAW STATION FAILURE COUNTS")

        raw = con.execute("""
            SELECT
                station_id,
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
                    WHERE event_type = 'abandoned_queue'
                ) AS abandoned_attempts

            FROM swap_events
            GROUP BY station_id
        """).fetchdf()

        # Validate the component counts.
        raw["count_check"] = (
            raw["failed_attempts"]
            == (
                raw["no_battery_failures"]
                + raw["system_error_failures"]
            )
        )

        raw["rate_check"] = (
            raw["failed_attempts"] <= raw["total_attempts"]
        )

        raw["failure_rate_pct"] = (
            100 * raw["failed_attempts"]
            / raw["total_attempts"]
        ).round(2)

        print("\nCount consistency:")
        print(raw["count_check"].value_counts().to_string())

        print("\nFailure counts within total attempts:")
        print(raw["rate_check"].value_counts().to_string())

        print("\nTop 10 stations by raw failure rate:")
        print(
            raw.sort_values(
                "failure_rate_pct",
                ascending=False
            ).head(10).to_string(index=False)
        )

        output = config.TABLES_DIR / "station_failure_diagnostic.csv"
        raw.to_csv(output, index=False)

        print(f"\nSaved diagnostic: {output}")

    finally:
        con.close()


if __name__ == "__main__":
    main()