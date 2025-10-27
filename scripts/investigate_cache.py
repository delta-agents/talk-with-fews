#!/usr/bin/env python3
"""
Script to investigate the saved webservice cache databases.

This script allows you to explore the ingested data from FEWS webservices
that has been saved to DuckDB files for debugging and investigation.

To enable database saving, set: DEV_SAVE_WEBSERVICE_CACHE=true

Usage:
    python scripts/investigate_cache.py [database_file]

If no database file is provided, it will list all available cache files.
"""

import sys
from pathlib import Path
import duckdb
import pandas as pd


def list_cache_files():
    """List all available cache files."""
    cache_dir = Path("data/webservice_cache")
    if not cache_dir.exists():
        print("No cache directory found at data/webservice_cache")
        return []

    cache_files = list(cache_dir.glob("*.duckdb"))
    if not cache_files:
        print("No cache files found")
        return []

    print("Available cache files:")
    for i, file in enumerate(cache_files, 1):
        print(f"  {i}. {file.name}")

    return cache_files


def investigate_database(db_path: str):
    """Investigate a specific database file."""
    print(f"\nInvestigating database: {db_path}")
    print("=" * 50)

    # Check if it's a directory (EXPORT DATABASE creates a directory)
    if Path(db_path).is_dir():
        print("📁 This is an exported database directory")
        print("Contents:")
        for file in sorted(Path(db_path).iterdir()):
            size = file.stat().st_size
            print(f"  - {file.name} ({size:,} bytes)")

        # Show CSV data directly instead of SQL files
        print("\n📊 Data Analysis:")

        # Analyze locations.csv
        locations_file = Path(db_path) / "locations.csv"
        if locations_file.exists():
            print("\n--- LOCATIONS ---")
            df_locations = pd.read_csv(locations_file)
            print(f"Row count: {len(df_locations)}")
            print(f"Columns: {list(df_locations.columns)}")
            if len(df_locations) > 0:
                print("\nSample locations:")
                sample_cols = (
                    ["locationId", "shortName", "lat", "lon"]
                    if all(
                        col in df_locations.columns
                        for col in ["locationId", "shortName", "lat", "lon"]
                    )
                    else df_locations.columns[:4]
                )
                print(df_locations[sample_cols].head(3).to_string(index=False))

        # Analyze parameters.csv
        parameters_file = Path(db_path) / "parameters.csv"
        if parameters_file.exists():
            print("\n--- PARAMETERS ---")
            df_parameters = pd.read_csv(parameters_file)
            print(f"Row count: {len(df_parameters)}")
            print(f"Columns: {list(df_parameters.columns)}")
            if len(df_parameters) > 0:
                print("\nSample parameters:")
                sample_cols = (
                    ["id", "name", "unit"]
                    if all(
                        col in df_parameters.columns for col in ["id", "name", "unit"]
                    )
                    else df_parameters.columns[:3]
                )
                print(df_parameters[sample_cols].head(3).to_string(index=False))

        # Analyze series_headers.csv
        series_headers_file = Path(db_path) / "series_headers.csv"
        if series_headers_file.exists():
            print("\n--- SERIES HEADERS ---")
            df_series = pd.read_csv(series_headers_file)
            print(f"Row count: {len(df_series)}")
            print(f"Columns: {list(df_series.columns)}")
            if len(df_series) > 0:
                print("\nSample series headers:")
                sample_cols = (
                    ["locationId", "parameterId", "first_value_time", "last_value_time"]
                    if all(
                        col in df_series.columns
                        for col in [
                            "locationId",
                            "parameterId",
                            "first_value_time",
                            "last_value_time",
                        ]
                    )
                    else df_series.columns[:4]
                )
                print(df_series[sample_cols].head(3).to_string(index=False))

        return

    # Connect to the database (single file)
    conn = duckdb.connect(db_path)

    # Get list of tables
    tables = conn.execute("SHOW TABLES").fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"  - {table[0]}")

    # Show table schemas and row counts
    for table_name in [t[0] for t in tables]:
        print(f"\n--- {table_name.upper()} ---")

        # Get row count
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Row count: {count}")

        # Show schema
        schema = conn.execute(f"DESCRIBE {table_name}").fetchall()
        print("Schema:")
        for col in schema:
            print(f"  {col[0]}: {col[1]}")

        # Show sample data (first 5 rows)
        if count > 0:
            print("\nSample data (first 5 rows):")
            sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
            columns = [
                desc[0] for desc in conn.execute(f"DESCRIBE {table_name}").fetchall()
            ]
            df = pd.DataFrame(sample, columns=columns)
            print(df.to_string(index=False))
        else:
            print("No data in table")

    conn.close()


def main():
    if len(sys.argv) > 1:
        # Investigate specific database file
        db_path = sys.argv[1]
        if not Path(db_path).exists():
            print(f"Database file not found: {db_path}")
            return
        investigate_database(db_path)
    else:
        # List available files
        cache_files = list_cache_files()
        if cache_files:
            print("\nTo investigate a specific database, run:")
            print("python scripts/investigate_cache.py <database_file>")
            print("\nExample:")
            print(f"python scripts/investigate_cache.py {cache_files[0]}")


if __name__ == "__main__":
    main()
