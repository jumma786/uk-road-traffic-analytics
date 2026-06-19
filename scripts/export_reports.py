"""
Export business query results to CSV files in the reports/ directory.

Usage:
    python scripts/export_reports.py
    python scripts/export_reports.py --query covid_impact
    python scripts/export_reports.py --server MY_SERVER --database MY_DB
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import SQL_SERVER, SQL_DATABASE, REPORTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

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
    "covid_impact": """
        SELECT
            d.Year,
            SUM(f.CarsAndTaxis) AS Cars,
            SUM(f.BusesAndCoaches) AS Buses,
            SUM(f.LGVs) AS LGVs,
            SUM(f.AllHGVs) AS HGVs,
            SUM(f.PedalCycles) AS Cycles,
            SUM(f.AllMotorVehicles) AS AllMotor
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year BETWEEN 2019 AND 2023
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "cycling_trends": """
        SELECT
            d.Year,
            SUM(f.PedalCycles) AS TotalCycles,
            SUM(f.AllMotorVehicles) AS TotalMotor,
            ROUND(SUM(f.PedalCycles) * 100.0 /
                NULLIF(SUM(f.AllMotorVehicles) + SUM(f.PedalCycles), 0), 4
            ) AS CycleSharePct
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "lgv_ecommerce_trend": """
        SELECT
            d.Year,
            SUM(f.LGVs) AS TotalLGVs,
            SUM(f.AllMotorVehicles) AS TotalMotor,
            ROUND(SUM(f.LGVs) * 100.0 /
                NULLIF(SUM(f.AllMotorVehicles), 0), 2
            ) AS LGV_SharePct
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "motorway_vs_aroad": """
        SELECT
            d.Year,
            SUM(CASE WHEN cp.RoadCategory IN ('TM', 'PM')
                THEN f.AllMotorVehicles ELSE 0 END) AS Motorway_Flow,
            SUM(CASE WHEN cp.RoadCategory IN ('TA', 'PA')
                THEN f.AllMotorVehicles ELSE 0 END) AS ARoad_Flow,
            SUM(CASE WHEN cp.RoadCategory IN ('M', 'MB', 'MCU')
                THEN f.AllMotorVehicles ELSE 0 END) AS Minor_Flow
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "hgv_axle_breakdown": """
        SELECT
            d.Year,
            SUM(f.HGVs2RigidAxle) AS Rigid2,
            SUM(f.HGVs3RigidAxle) AS Rigid3,
            SUM(f.HGVs4OrMoreRigidAxle) AS Rigid4Plus,
            SUM(f.HGVs3Or4ArticulatedAxle) AS Artic3_4,
            SUM(f.HGVs5ArticulatedAxle) AS Artic5,
            SUM(f.HGVs6ArticulatedAxle) AS Artic6,
            SUM(f.AllHGVs) AS TotalHGV
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "bus_coach_decline": """
        SELECT
            d.Year,
            SUM(f.BusesAndCoaches) AS TotalBuses,
            SUM(f.AllMotorVehicles) AS TotalMotor,
            ROUND(SUM(f.BusesAndCoaches) * 100.0 /
                NULLIF(SUM(f.AllMotorVehicles), 0), 3) AS Bus_SharePct
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "motorcycle_trends": """
        SELECT
            d.Year,
            SUM(f.TwoWheeledMotorVehicles) AS TotalMotorcycles,
            ROUND(SUM(f.TwoWheeledMotorVehicles) * 100.0 /
                NULLIF(SUM(f.AllMotorVehicles), 0), 3) AS Motorcycle_SharePct
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
}


def get_connection(server: str, database: str) -> pyodbc.Connection:
    driver = "{ODBC Driver 17 for SQL Server}"
    conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)


def main():
    parser = argparse.ArgumentParser(description="Export business query results to CSV")
    parser.add_argument("--server", default=SQL_SERVER, help="SQL Server instance")
    parser.add_argument("--database", default=SQL_DATABASE, help="Target database")
    parser.add_argument(
        "--query", choices=list(QUERIES.keys()),
        help="Run a single query (default: all)",
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)

    logger.info("Connecting to %s/%s...", args.server, args.database)
    conn = get_connection(args.server, args.database)

    queries_to_run = {args.query: QUERIES[args.query]} if args.query else QUERIES

    for name, sql in queries_to_run.items():
        output_path = REPORTS_DIR / f"{name}.csv"
        try:
            df = pd.read_sql(sql, conn)
            df.to_csv(output_path, index=False)
            logger.info("  %s: %d rows -> %s", name, len(df), output_path.name)
        except Exception as e:
            logger.error("  %s: ERROR - %s", name, e)

    conn.close()
    logger.info("Done. Reports saved to %s/", REPORTS_DIR)


if __name__ == "__main__":
    main()
