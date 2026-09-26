
"""
VoltRelay Energy Analytics
File: src/data_loader.py

Purpose:
1. Load the smaller CSV datasets using Pandas.
2. Inspect large compressed CSV files using DuckDB.
3. Generate dataset summaries and data quality reports.
4. Avoid loading millions of rows into memory unnecessarily.
"""

from pathlib import Path

import duckdb
import pandas as pd

import config


# ==================================================
# 1. LOAD SMALL DATASETS
# ==================================================

def load_small_datasets():
    """
    Load the seven smaller CSV datasets into Pandas.

    Returns
    -------
    dict
        Dictionary containing the loaded DataFrames.
    """

    print("\n" + "=" * 65)
    print("LOADING SMALL DATASETS")
    print("=" * 65)

    files = {
        "riders": config.RIDERS_FILE,
        "batteries": config.BATTERIES_FILE,
        "support_tickets": config.SUPPORT_TICKETS_FILE,
        "stations": config.STATIONS_FILE,
        "city_context": config.CITY_CONTEXT_FILE,
        "fleet_partners": config.FLEET_PARTNERS_FILE,
    }

    datasets = {}

    for name, file_path in files.items():

        if not file_path.exists():
            print(f"WARNING: {name} file not found: {file_path}")
            continue

        try:
            df = pd.read_csv(file_path, low_memory=False)

            datasets[name] = df

            print(
                f"{name:20s} | "
                f"Rows: {len(df):>10,} | "
                f"Columns: {len(df.columns):>3}"
            )

        except Exception as error:
            print(f"ERROR loading {name}: {error}")

    return datasets


# ==================================================
# 2. CONNECT TO DUCKDB
# ==================================================

def get_connection():
    """
    Create a DuckDB connection.

    DuckDB will use a persistent local database file
    so we can reuse it for later analysis.
    """

    database_path = (
        config.PROCESSED_DATA_DIR / "voltrelay.duckdb"
    )

    connection = duckdb.connect(
        str(database_path)
    )

    # Limit DuckDB threads to avoid overwhelming
    # the computer during large CSV processing.
    connection.execute("SET threads TO 4")

    # Allow DuckDB to use disk space for intermediate
    # operations when RAM is limited.
    temp_directory = (
        config.PROCESSED_DATA_DIR / "duckdb_temp"
    )

    temp_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    connection.execute(
        f"SET temp_directory = '{str(temp_directory).replace(chr(92), '/')}'"
    )

    return connection


# ==================================================
# 3. REGISTER LARGE CSV FILES
# ==================================================



def register_large_datasets(connection):
    """Register large CSV datasets as DuckDB views."""

    large_files = {
        "swap_events": config.SWAP_EVENTS_FILE,
        "station_hourly_status": config.STATION_HOURLY_FILE,
    }

    print("\n" + "=" * 65)
    print("REGISTERING LARGE DATASETS")
    print("=" * 65)

    for table_name, file_path in large_files.items():

        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            continue

        safe_path = str(file_path).replace("\\", "/").replace("'", "''")

        query = f"""
            CREATE OR REPLACE VIEW {table_name} AS
            SELECT *
            FROM read_csv(
                '{safe_path}',
                auto_detect = true,
                delim = ',',
                quote = '"',
                escape = '"',
                header = true,
                null_padding = true,
                strict_mode = false,
                max_line_size = 10000000,
                sample_size = 20000
            )
        """

        try:
            connection.execute(query)

            # Verify that DuckDB can read the view
            preview = connection.execute(
                f"SELECT * FROM {table_name} LIMIT 5"
            ).fetchdf()

            print(f"\nRegistered and tested: {table_name}")
            print(f"Preview shape: {preview.shape}")
            print(preview.head(2).to_string(index=False))

        except Exception as error:
            print(f"\nERROR registering {table_name}:")
            print(error)

    return connection


# ==================================================
# 4. GET LARGE DATASET ROW COUNTS
# ==================================================

def get_large_dataset_counts(connection):
    """
    Get row counts for the large datasets.

    Note: Counting compressed CSV records requires
    reading the file. It may take a few minutes.
    """

    print("\n" + "=" * 65)
    print("LARGE DATASET ROW COUNTS")
    print("=" * 65)

    tables = [
        "swap_events",
        "station_hourly_status"
    ]

    results = []

    for table_name in tables:

        try:
            query = f"""
                SELECT COUNT(*) AS total_rows
                FROM {table_name}
            """

            count = connection.execute(
                query
            ).fetchone()[0]

            results.append({
                "dataset": table_name,
                "rows": count
            })

            print(
                f"{table_name:25s}: {count:,} rows"
            )

        except Exception as error:
            print(
                f"Could not count {table_name}: "
                f"{error}"
            )

    return pd.DataFrame(results)


# ==================================================
# 5. DISPLAY LARGE DATASET SCHEMAS
# ==================================================

def inspect_large_schemas(connection):
    """
    Inspect the column names and data types
    of the two large datasets.
    """

    print("\n" + "=" * 65)
    print("LARGE DATASET SCHEMAS")
    print("=" * 65)

    tables = [
        "swap_events",
        "station_hourly_status"
    ]

    schema_results = []

    for table_name in tables:

        try:
            schema = connection.execute(
                f"DESCRIBE SELECT * FROM {table_name}"
            ).df()

            schema.insert(
                0,
                "dataset",
                table_name
            )

            schema_results.append(schema)

            print(f"\n{table_name.upper()}")

            print(
                schema[
                    ["column_name", "column_type"]
                ].to_string(index=False)
            )

        except Exception as error:
            print(
                f"Schema inspection failed for "
                f"{table_name}: {error}"
            )

    if schema_results:
        combined_schema = pd.concat(
            schema_results,
            ignore_index=True
        )

        schema_file = (
            config.TABLES_DIR / "large_dataset_schema.csv"
        )

        combined_schema.to_csv(
            schema_file,
            index=False
        )

        print(
            f"\nSchema saved to: {schema_file}"
        )

        return combined_schema

    return pd.DataFrame()


# ==================================================
# 6. PREVIEW LARGE DATASETS
# ==================================================

def preview_large_datasets(connection, rows=5):
    """
    Display a small sample from each large dataset.
    """

    print("\n" + "=" * 65)
    print("LARGE DATASET SAMPLE RECORDS")
    print("=" * 65)

    tables = [
        "swap_events",
        "station_hourly_status"
    ]

    for table_name in tables:

        try:
            sample = connection.execute(
                f"""
                SELECT *
                FROM {table_name}
                LIMIT {int(rows)}
                """
            ).df()

            print(f"\n{table_name.upper()} SAMPLE")

            print(sample.to_string(index=False))

        except Exception as error:
            print(
                f"Preview failed for {table_name}: "
                f"{error}"
            )


# ==================================================
# 7. GENERATE SMALL DATASET SUMMARY
# ==================================================

def summarize_small_datasets(datasets):
    """
    Create a summary of the smaller datasets,
    including row counts, columns and missing values.
    """

    print("\n" + "=" * 65)
    print("SMALL DATASET QUALITY SUMMARY")
    print("=" * 65)

    summary = []

    for name, df in datasets.items():

        missing_cells = int(
            df.isna().sum().sum()
        )

        total_cells = (
            df.shape[0] * df.shape[1]
        )

        missing_pct = (
            missing_cells / total_cells * 100
            if total_cells > 0
            else 0
        )

        summary.append({
            "dataset": name,
            "rows": len(df),
            "columns": len(df.columns),
            "missing_cells": missing_cells,
            "missing_percentage": round(
                missing_pct, 2
            ),
            "duplicate_rows": int(
                df.duplicated().sum()
            )
        })

        print(
            f"{name:20s} | "
            f"Rows: {len(df):>8,} | "
            f"Missing: {missing_pct:>6.2f}%"
        )

    summary_df = pd.DataFrame(summary)

    summary_file = (
        config.TABLES_DIR / "small_dataset_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False
    )

    print(
        f"\nSummary saved to: {summary_file}"
    )

    return summary_df


# ==================================================
# 8. MAIN EXECUTION
# ==================================================

def main():

    print("\n")
    print("*" * 65)
    print("VOLTRELAY ENERGY - DATA LOADING PIPELINE")
    print("*" * 65)

    # Load small tables
    datasets = load_small_datasets()

    # Create DuckDB connection
    connection = get_connection()

    try:

        # Register large CSV files
        register_large_datasets(connection)

        # Get large file counts
        large_counts = get_large_dataset_counts(
            connection
        )

        # Inspect schemas
        inspect_large_schemas(connection)

        # Preview data
        preview_large_datasets(connection)

        # Summarize smaller datasets
        small_summary = summarize_small_datasets(
            datasets
        )

        print("\n" + "=" * 65)
        print("DATA LOADING COMPLETED")
        print("=" * 65)

        print(
            "\nSmall datasets loaded:",
            len(datasets)
        )

        print(
            "Large datasets inspected:",
            len(large_counts)
        )

        print(
            "\nDuckDB database:",
            config.PROCESSED_DATA_DIR
            / "voltrelay.duckdb"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()