"""
Export business query results to CSV files in the reports/ directory.

Usage:
    python scripts/export_reports.py --server YOUR_SERVER --database UK_Road_Traffic_DW
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyodbc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

QUERIES = {
    "regional_traffic_summary": """
        SELECT
            r.RegionName,
            SUM(f.AllMotorVehicles) AS TotalMotorVehicles,
            SUM(f.AllHGVs) AS TotalHGVs,
            SUM(f.AllMotorVehicles + f.PedalCycles) AS TotalAllVehicles
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = 2023
        GROUP BY r.RegionName
        ORDER BY TotalAllVehicles DESC
    """,
    "top_busiest_roads": """
        SELECT TOP 10
            cp.RoadName,
            cp.RoadCategory,
            SUM(f.AllMotorVehicles) AS TotalTraffic,
            AVG(f.AllMotorVehicles) AS AvgDailyFlow
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year >= 2020
        GROUP BY cp.RoadName, cp.RoadCategory
        HAVING SUM(f.AllMotorVehicles) > 1000000
        ORDER BY TotalTraffic DESC
    """,
    "yoy_growth_trend": """
        WITH YearlyTraffic AS (
            SELECT
                d.Year,
                SUM(f.AllMotorVehicles) AS TotalTraffic
            FROM FactTrafficFlowDirection f
            JOIN DimDate d ON f.DateKey = d.DateKey
            GROUP BY d.Year
        )
        SELECT
            Year,
            TotalTraffic,
            LAG(TotalTraffic) OVER (ORDER BY Year) AS PrevYear,
            ROUND(
                (TotalTraffic - LAG(TotalTraffic) OVER (ORDER BY Year)) * 100.0 /
                NULLIF(LAG(TotalTraffic) OVER (ORDER BY Year), 0), 2
            ) AS YoY_GrowthPct
        FROM YearlyTraffic
    """,
    "hgv_passenger_mix": """
        SELECT
            r.RegionName,
            SUM(f.AllHGVs) AS HGV_Total,
            SUM(f.CarsAndTaxis + f.LGVs) AS Passenger_Total,
            ROUND(SUM(f.AllHGVs) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 2) AS HGV_Pct
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        GROUP BY r.RegionName
        ORDER BY HGV_Pct DESC
    """,
    "local_authority_growth": """
        WITH LAGrowth AS (
            SELECT
                la.LocalAuthorityName,
                d.Year,
                SUM(f.AllMotorVehicles) AS TotalTraffic
            FROM FactTrafficFlowDirection f
            JOIN DimLocalAuthority la ON f.LocalAuthorityKey = la.LocalAuthorityKey
            JOIN DimDate d ON f.DateKey = d.DateKey
            WHERE d.Year IN (2018, 2023)
            GROUP BY la.LocalAuthorityName, d.Year
        )
        SELECT
            LocalAuthorityName,
            MAX(CASE WHEN Year = 2023 THEN TotalTraffic END) AS Traffic2023,
            MAX(CASE WHEN Year = 2018 THEN TotalTraffic END) AS Traffic2018,
            ROUND(
                (MAX(CASE WHEN Year = 2023 THEN TotalTraffic END) -
                 MAX(CASE WHEN Year = 2018 THEN TotalTraffic END)) * 100.0 /
                NULLIF(MAX(CASE WHEN Year = 2018 THEN TotalTraffic END), 0), 2
            ) AS GrowthPct
        FROM LAGrowth
        GROUP BY LocalAuthorityName
        HAVING MAX(CASE WHEN Year = 2018 THEN TotalTraffic END) IS NOT NULL
        ORDER BY GrowthPct DESC
    """,
    "road_category_distribution": """
        SELECT
            cp.RoadCategory,
            COUNT(DISTINCT cp.CountPointID) AS NumCountPoints,
            SUM(f.AllMotorVehicles) AS TotalTraffic,
            AVG(f.AllMotorVehicles) AS AvgFlowPerPoint
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        GROUP BY cp.RoadCategory
        ORDER BY TotalTraffic DESC
    """,
    "geospatial_hotspots": """
        SELECT
            cp.Latitude,
            cp.Longitude,
            cp.RoadName,
            r.RegionName,
            la.LocalAuthorityName,
            SUM(f.AllMotorVehicles) AS TotalTraffic,
            AVG(f.AllMotorVehicles) AS AvgDailyFlow
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimLocalAuthority la ON f.LocalAuthorityKey = la.LocalAuthorityKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = 2023
        GROUP BY cp.Latitude, cp.Longitude, cp.RoadName,
                 r.RegionName, la.LocalAuthorityName
        HAVING SUM(f.AllMotorVehicles) > 50000
        ORDER BY TotalTraffic DESC
    """,
}


def get_connection(server: str, database: str) -> pyodbc.Connection:
    driver = "{ODBC Driver 17 for SQL Server}"
    conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)


def main():
    parser = argparse.ArgumentParser(description="Export business query results to CSV")
    parser.add_argument("--server", required=True, help="SQL Server instance")
    parser.add_argument("--database", default="UK_Road_Traffic_DW", help="Target database")
    parser.add_argument("--query", choices=list(QUERIES.keys()), help="Run a single query (default: all)")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)

    print(f"Connecting to {args.server}/{args.database}...")
    conn = get_connection(args.server, args.database)

    queries_to_run = {args.query: QUERIES[args.query]} if args.query else QUERIES

    for name, sql in queries_to_run.items():
        output_path = REPORTS_DIR / f"{name}.csv"
        try:
            df = pd.read_sql(sql, conn)
            df.to_csv(output_path, index=False)
            print(f"  {name}: {len(df)} rows -> {output_path.name}")
        except Exception as e:
            print(f"  {name}: ERROR - {e}", file=sys.stderr)

    conn.close()
    print(f"\nDone. Reports saved to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
