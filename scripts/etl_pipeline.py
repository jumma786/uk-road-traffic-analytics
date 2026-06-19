"""
ETL Pipeline: Load UK road traffic data from CSV into SQL Server star schema.

Usage:
    python scripts/etl_pipeline.py --server YOUR_SERVER --database UK_Road_Traffic_DW
    python scripts/etl_pipeline.py --server localhost\\SQLEXPRESS --database UK_Road_Traffic_DW
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyodbc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DIRECTION_FILE = RAW_DIR / "dft_traffic_counts_aadf_by_direction.csv"
COUNT_POINTS_FILE = RAW_DIR / "count_points.csv"


def get_connection(server: str, database: str, trusted: bool = True) -> pyodbc.Connection:
    driver = "{ODBC Driver 17 for SQL Server}"
    if trusted:
        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};"
    return pyodbc.connect(conn_str)


def truncate_tables(cursor: pyodbc.Cursor):
    print("Truncating existing data...")
    cursor.execute("DELETE FROM FactTrafficFlowDirection")
    cursor.execute("DELETE FROM DimCountPoint")
    cursor.execute("DELETE FROM DimLocalAuthority")
    cursor.execute("DELETE FROM DimRegion")
    cursor.execute("DELETE FROM DimDate")
    cursor.commit()
    print("All tables truncated.")


def load_dim_date(cursor: pyodbc.Cursor, df: pd.DataFrame) -> int:
    years = sorted(df["year"].dropna().unique())
    rows = []
    for year in years:
        for month in range(1, 13):
            try:
                date = pd.Timestamp(year=int(year), month=month, day=1)
            except (ValueError, OverflowError):
                continue
            date_key = int(f"{int(year)}{month:02d}")
            fiscal_year = int(year) if month >= 4 else int(year) - 1
            rows.append((
                date_key,
                date.strftime("%Y-%m-%d"),
                int(year),
                (month - 1) // 3 + 1,
                month,
                date.strftime("%B"),
                1,
                date.dayofweek + 1,
                date.strftime("%A"),
                0,
                fiscal_year,
            ))

    sql = """INSERT INTO DimDate (DateKey, FullDate, Year, Quarter, Month, MonthName,
             Day, DayOfWeek, DayName, IsWeekend, FiscalYear)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    cursor.executemany(sql, rows)
    cursor.commit()
    print(f"  DimDate: {len(rows)} rows loaded")
    return len(rows)


def load_dim_region(cursor: pyodbc.Cursor, df: pd.DataFrame) -> dict:
    regions = (
        df[["region_id", "region_name", "region_ons_code"]]
        .drop_duplicates(subset=["region_id"])
        .dropna(subset=["region_id"])
        .sort_values("region_id")
    )

    sql = """INSERT INTO DimRegion (RegionID, RegionName, RegionONSCode)
             OUTPUT INSERTED.RegionKey, INSERTED.RegionID
             VALUES (?, ?, ?)"""

    lookup = {}
    for _, row in regions.iterrows():
        cursor.execute(sql, (
            int(row["region_id"]),
            str(row["region_name"]) if pd.notna(row["region_name"]) else None,
            str(row["region_ons_code"]) if pd.notna(row["region_ons_code"]) else None,
        ))
        result = cursor.fetchone()
        lookup[int(row["region_id"])] = result[0]
    cursor.commit()
    print(f"  DimRegion: {len(lookup)} rows loaded")
    return lookup


def load_dim_local_authority(cursor: pyodbc.Cursor, df: pd.DataFrame, region_lookup: dict) -> dict:
    las = (
        df[["local_authority_id", "region_id", "local_authority_name", "local_authority_code"]]
        .drop_duplicates(subset=["local_authority_id"])
        .dropna(subset=["local_authority_id"])
        .sort_values("local_authority_id")
    )

    sql = """INSERT INTO DimLocalAuthority (LocalAuthorityID, RegionKey, LocalAuthorityName, LocalAuthorityCode)
             OUTPUT INSERTED.LocalAuthorityKey, INSERTED.LocalAuthorityID
             VALUES (?, ?, ?, ?)"""

    lookup = {}
    for _, row in las.iterrows():
        region_key = region_lookup.get(int(row["region_id"])) if pd.notna(row["region_id"]) else None
        cursor.execute(sql, (
            int(row["local_authority_id"]),
            region_key,
            str(row["local_authority_name"]) if pd.notna(row["local_authority_name"]) else None,
            str(row["local_authority_code"]) if pd.notna(row["local_authority_code"]) else None,
        ))
        result = cursor.fetchone()
        lookup[int(row["local_authority_id"])] = result[0]
    cursor.commit()
    print(f"  DimLocalAuthority: {len(lookup)} rows loaded")
    return lookup


def load_dim_count_point(cursor: pyodbc.Cursor, df: pd.DataFrame) -> dict:
    cps = (
        df[["count_point_id", "road_name", "road_category", "road_type",
            "latitude", "longitude", "link_length_km"]]
        .drop_duplicates(subset=["count_point_id"])
        .dropna(subset=["count_point_id"])
        .sort_values("count_point_id")
    )

    sql = """INSERT INTO DimCountPoint (CountPointID, RoadName, RoadCategory, RoadType,
             Latitude, Longitude, LinkLengthKm)
             OUTPUT INSERTED.CountPointKey, INSERTED.CountPointID
             VALUES (?, ?, ?, ?, ?, ?, ?)"""

    lookup = {}
    for _, row in cps.iterrows():
        cursor.execute(sql, (
            int(row["count_point_id"]),
            str(row["road_name"]) if pd.notna(row["road_name"]) else None,
            str(row["road_category"]) if pd.notna(row["road_category"]) else None,
            str(row["road_type"]) if pd.notna(row["road_type"]) else None,
            float(row["latitude"]) if pd.notna(row["latitude"]) else None,
            float(row["longitude"]) if pd.notna(row["longitude"]) else None,
            float(row["link_length_km"]) if pd.notna(row["link_length_km"]) else None,
        ))
        result = cursor.fetchone()
        lookup[int(row["count_point_id"])] = result[0]
    cursor.commit()
    print(f"  DimCountPoint: {len(lookup)} rows loaded")
    return lookup


def load_fact_table(
    cursor: pyodbc.Cursor,
    df: pd.DataFrame,
    region_lookup: dict,
    la_lookup: dict,
    cp_lookup: dict,
    batch_size: int = 5000,
) -> int:
    vehicle_cols = [
        ("pedal_cycles", "PedalCycles"),
        ("two_wheeled_motor_vehicles", "TwoWheeledMotorVehicles"),
        ("cars_and_taxis", "CarsAndTaxis"),
        ("buses_and_coaches", "BusesAndCoaches"),
        ("LGVs", "LGVs"),
        ("HGVs_2_rigid_axle", "HGVs2RigidAxle"),
        ("HGVs_3_rigid_axle", "HGVs3RigidAxle"),
        ("HGVs_4_or_more_rigid_axle", "HGVs4OrMoreRigidAxle"),
        ("HGVs_3_or_4_articulated_axle", "HGVs3Or4ArticulatedAxle"),
        ("HGVs_5_articulated_axle", "HGVs5ArticulatedAxle"),
        ("HGVs_6_articulated_axle", "HGVs6ArticulatedAxle"),
        ("all_HGVs", "AllHGVs"),
        ("all_motor_vehicles", "AllMotorVehicles"),
    ]

    sql = """INSERT INTO FactTrafficFlowDirection
             (DateKey, CountPointKey, LocalAuthorityKey, RegionKey,
              DirectionOfTravel, PedalCycles, TwoWheeledMotorVehicles,
              CarsAndTaxis, BusesAndCoaches, LGVs,
              HGVs2RigidAxle, HGVs3RigidAxle, HGVs4OrMoreRigidAxle,
              HGVs3Or4ArticulatedAxle, HGVs5ArticulatedAxle, HGVs6ArticulatedAxle,
              AllHGVs, AllMotorVehicles)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    total = len(df)
    loaded = 0
    skipped = 0
    batch = []

    for _, row in df.iterrows():
        year = row.get("year")
        month = row.get("month", 1) if "month" in df.columns else 1
        date_key = int(f"{int(year)}{int(month):02d}") if pd.notna(year) else None

        cp_id = int(row["count_point_id"]) if pd.notna(row["count_point_id"]) else None
        la_id = int(row["local_authority_id"]) if pd.notna(row["local_authority_id"]) else None
        region_id = int(row["region_id"]) if pd.notna(row["region_id"]) else None

        cp_key = cp_lookup.get(cp_id)
        la_key = la_lookup.get(la_id)
        region_key = region_lookup.get(region_id)

        if date_key is None or cp_key is None:
            skipped += 1
            continue

        direction = str(row["direction_of_travel"]) if pd.notna(row.get("direction_of_travel")) else None

        values = [date_key, cp_key, la_key, region_key, direction]
        for src_col, _ in vehicle_cols:
            val = row.get(src_col)
            values.append(float(val) if pd.notna(val) else None)

        batch.append(tuple(values))

        if len(batch) >= batch_size:
            cursor.executemany(sql, batch)
            cursor.commit()
            loaded += len(batch)
            batch = []
            print(f"  FactTrafficFlowDirection: {loaded:,}/{total:,} rows loaded...", end="\r")

    if batch:
        cursor.executemany(sql, batch)
        cursor.commit()
        loaded += len(batch)

    print(f"  FactTrafficFlowDirection: {loaded:,} rows loaded, {skipped:,} skipped")
    return loaded


def main():
    parser = argparse.ArgumentParser(description="ETL: Load UK traffic data into SQL Server star schema")
    parser.add_argument("--server", required=True, help="SQL Server instance (e.g. localhost\\SQLEXPRESS)")
    parser.add_argument("--database", default="UK_Road_Traffic_DW", help="Target database name")
    parser.add_argument("--no-truncate", action="store_true", help="Skip truncating tables before load")
    parser.add_argument("--batch-size", type=int, default=5000, help="Fact table insert batch size")
    args = parser.parse_args()

    if not DIRECTION_FILE.exists():
        print(f"Error: Source file not found: {DIRECTION_FILE}")
        sys.exit(1)

    print(f"Connecting to {args.server}/{args.database}...")
    conn = get_connection(args.server, args.database)
    cursor = conn.cursor()

    print(f"Reading {DIRECTION_FILE.name}...")
    df = pd.read_csv(DIRECTION_FILE, low_memory=False)
    print(f"  {len(df):,} rows, {len(df.columns)} columns")

    if not args.no_truncate:
        truncate_tables(cursor)

    print("\nLoading dimensions...")
    load_dim_date(cursor, df)
    region_lookup = load_dim_region(cursor, df)
    la_lookup = load_dim_local_authority(cursor, df, region_lookup)
    cp_lookup = load_dim_count_point(cursor, df)

    print("\nLoading fact table...")
    fact_count = load_fact_table(cursor, df, region_lookup, la_lookup, cp_lookup, args.batch_size)

    cursor.close()
    conn.close()

    print(f"\nETL complete. {fact_count:,} fact rows loaded.")


if __name__ == "__main__":
    main()
