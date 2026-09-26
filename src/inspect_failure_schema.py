import duckdb

from src import config


def main():

    db_path = config.PROCESSED_DATA_DIR / "voltrelay.duckdb"

    con = duckdb.connect(str(db_path), read_only=True)

    tables = [
        "swap_events",
        "station_hourly_status",
        "stations",
        "batteries",
    ]

    for table in tables:

        print("\n" + "=" * 70)
        print(f"SCHEMA: {table}")
        print("=" * 70)

        result = con.execute(
            f"DESCRIBE SELECT * FROM {table}"
        ).fetchdf()

        print(result[["column_name", "column_type"]].to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()