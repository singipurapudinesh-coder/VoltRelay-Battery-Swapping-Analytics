
"""
VoltRelay Energy Analytics
File: src/config.py

Central configuration for file paths, data processing,
and analysis settings.
"""

from pathlib import Path

# --------------------------------------------------
# 1. PROJECT DIRECTORIES
# --------------------------------------------------

# Root directory of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Main directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "outputs"

NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
REPORT_DIR = PROJECT_ROOT / "reports"


# --------------------------------------------------
# 2. RAW DATA FILE PATHS
# --------------------------------------------------

SWAP_EVENTS_FILE = RAW_DATA_DIR / "swap_events.csv"

STATION_HOURLY_FILE = (
    RAW_DATA_DIR / "station_hourly_status.csv"
)

RIDERS_FILE = RAW_DATA_DIR / "riders.csv"

BATTERIES_FILE = RAW_DATA_DIR / "batteries.csv"

SUPPORT_TICKETS_FILE = (
    RAW_DATA_DIR / "support_tickets.csv"
)

STATIONS_FILE = RAW_DATA_DIR / "stations.csv"

CITY_CONTEXT_FILE = (
    RAW_DATA_DIR / "city_daily_context.csv"
)

FLEET_PARTNERS_FILE = (
    RAW_DATA_DIR / "fleet_partners.csv"
)


# --------------------------------------------------
# 3. PROCESSED DATA DIRECTORIES
# --------------------------------------------------

CLEAN_SWAPS_DIR = PROCESSED_DATA_DIR / "clean_swaps"

CLEAN_STATION_HOURLY_DIR = (
    PROCESSED_DATA_DIR / "clean_station_hourly"
)

# Output files
RIDER_METRICS_FILE = (
    PROCESSED_DATA_DIR / "rider_metrics.csv"
)

STATION_METRICS_FILE = (
    PROCESSED_DATA_DIR / "station_metrics.csv"
)

MONTHLY_KPIS_FILE = (
    PROCESSED_DATA_DIR / "monthly_kpis.csv"
)


# --------------------------------------------------
# 4. ANALYSIS OUTPUT DIRECTORIES
# --------------------------------------------------

FIGURES_DIR = OUTPUT_DIR / "figures"

TABLES_DIR = OUTPUT_DIR / "tables"

FINDINGS_DIR = OUTPUT_DIR / "findings"

REPORT_FIGURES_DIR = REPORT_DIR / "figures"


# --------------------------------------------------
# 5. DATASET SETTINGS
# --------------------------------------------------

START_DATE = "2024-01-01"

END_DATE = "2025-06-30"

CITIES = [
    "Bengaluru",
    "Delhi NCR",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Jaipur",
]

# Process large CSV files in manageable chunks
CHUNK_SIZE = 200_000

# Maximum plausible distance per swap, in km.
# Used as an initial analytical screening threshold,
# not as a claim about the actual vehicle range.
MAX_PLAUSIBLE_KM = 500

# Dataset outcomes
COMPLETED_EVENT = "swap_completed"


# --------------------------------------------------
# 6. CREATE REQUIRED DIRECTORIES
# --------------------------------------------------

DIRECTORIES = [
    PROCESSED_DATA_DIR,
    OUTPUT_DIR,
    CLEAN_SWAPS_DIR,
    CLEAN_STATION_HOURLY_DIR,
    FIGURES_DIR,
    TABLES_DIR,
    FINDINGS_DIR,
    REPORT_DIR,
    REPORT_FIGURES_DIR,
]

for directory in DIRECTORIES:
    directory.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 7. CONFIGURATION CHECK
# --------------------------------------------------

if __name__ == "__main__":

    print("=" * 60)
    print("VOLTRELAY ENERGY ANALYTICS")
    print("=" * 60)

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw data folder: {RAW_DATA_DIR}")
    print(f"Processed data folder: {PROCESSED_DATA_DIR}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    print("\nRaw file availability:")

    raw_files = [
        SWAP_EVENTS_FILE,
        STATION_HOURLY_FILE,
        RIDERS_FILE,
        BATTERIES_FILE,
        SUPPORT_TICKETS_FILE,
        STATIONS_FILE,
        CITY_CONTEXT_FILE,
        FLEET_PARTNERS_FILE,
    ]

    for file_path in raw_files:
        status = "FOUND" if file_path.exists() else "MISSING"
        print(f"{file_path.name}: {status}")

    print("\nConfiguration loaded successfully.")