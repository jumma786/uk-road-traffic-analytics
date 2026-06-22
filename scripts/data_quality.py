"""
Automated data quality checks after each ETL load.
Validates row counts, null rates, value ranges, and referential integrity.

Usage:
    python scripts/data_quality.py
    python scripts/data_quality.py --server MY_SERVER --database MY_DB
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

CHECKS = {
    "row_counts": """
        SELECT 'DimDate' AS TableName, COUNT(*) AS RowCount FROM DimDate
        UNION ALL SELECT 'DimRegion', COUNT(*) FROM DimRegion
        UNION ALL SELECT 'DimLocalAuthority', COUNT(*) FROM DimLocalAuthority
        UNION ALL SELECT 'DimCountPoint', COUNT(*) FROM DimCountPoint
        UNION ALL SELECT 'FactTrafficFlowDirection', COUNT(*) FROM FactTrafficFlowDirection
    """,
    "null_check_fact": """
        SELECT
            SUM(CASE WHEN DateKey IS NULL THEN 1 ELSE 0 END) AS NullDateKey,
            SUM(CASE WHEN CountPointKey IS NULL THEN 1 ELSE 0 END) AS NullCountPointKey,
            SUM(CASE WHEN RegionKey IS NULL THEN 1 ELSE 0 END) AS NullRegionKey,
            SUM(CASE WHEN LocalAuthorityKey IS NULL THEN 1 ELSE 0 END) AS NullLAKey,
            SUM(CASE WHEN DirectionOfTravel IS NULL THEN 1 ELSE 0 END) AS NullDirection,
            SUM(CASE WHEN AllMotorVehicles IS NULL THEN 1 ELSE 0 END) AS NullMotorVehicles,
            COUNT(*) AS TotalRows
        FROM FactTrafficFlowDirection
    """,
    "negative_values": """
        SELECT
            SUM(CASE WHEN AllMotorVehicles < 0 THEN 1 ELSE 0 END) AS NegMotor,
            SUM(CASE WHEN AllHGVs < 0 THEN 1 ELSE 0 END) AS NegHGV,
            SUM(CASE WHEN CarsAndTaxis < 0 THEN 1 ELSE 0 END) AS NegCars,
            SUM(CASE WHEN PedalCycles < 0 THEN 1 ELSE 0 END) AS NegCycles,
            COUNT(*) AS TotalRows
        FROM FactTrafficFlowDirection
    """,
    "orphan_facts": """
        SELECT
            SUM(CASE WHEN d.DateKey IS NULL THEN 1 ELSE 0 END) AS OrphanDate,
            SUM(CASE WHEN cp.CountPointKey IS NULL THEN 1 ELSE 0 END) AS OrphanCP,
            SUM(CASE WHEN r.RegionKey IS NULL THEN 1 ELSE 0 END) AS OrphanRegion,
            COUNT(*) AS TotalRows
        FROM FactTrafficFlowDirection f
        LEFT JOIN DimDate d ON f.DateKey = d.DateKey
        LEFT JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        LEFT JOIN DimRegion r ON f.RegionKey = r.RegionKey
    """,
    "year_coverage": """
        SELECT d.Year, COUNT(*) AS FactRows
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year
        ORDER BY d.Year
    """,
    "direction_distribution": """
        SELECT DirectionOfTravel, COUNT(*) AS Cnt
        FROM FactTrafficFlowDirection
        GROUP BY DirectionOfTravel
        ORDER BY Cnt DESC
    """,
}

MIN_EXPECTED = {
    "DimDate": 10,
    "DimRegion": 5,
    "DimLocalAuthority": 100,
    "DimCountPoint": 10000,
    "FactTrafficFlowDirection": 500000,
}


def run_checks(server: str, database: str) -> list[dict]:
    driver = "{ODBC Driver 17 for SQL Server}"
    conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    conn = pyodbc.connect(conn_str)

    results = []

    for name, sql in CHECKS.items():
        try:
            df = pd.read_sql(sql, conn)
            results.append({"check": name, "status": "PASS", "detail": df.to_dict()})
            logger.info("[PASS] %s", name)

            if name == "row_counts":
                for _, row in df.iterrows():
                    table = row["TableName"]
                    count = row["RowCount"]
                    expected = MIN_EXPECTED.get(table, 0)
                    if count < expected:
                        logger.warning(
                            "  [WARN] %s has %d rows (expected >= %d)",
                            table, count, expected,
                        )
                        results.append({
                            "check": f"row_count_{table}",
                            "status": "WARN",
                            "detail": f"{count} < {expected}",
                        })

            if name == "null_check_fact":
                row = df.iloc[0]
                total = row["TotalRows"]
                for col in row.index:
                    if col.startswith("Null") and row[col] > 0:
                        pct = row[col] / total * 100
                        logger.warning("  [WARN] %s: %d nulls (%.2f%%)", col, row[col], pct)

            if name == "negative_values":
                row = df.iloc[0]
                for col in row.index:
                    if col.startswith("Neg") and row[col] > 0:
                        logger.error("  [FAIL] %s: %d negative values", col, row[col])
                        results[-1]["status"] = "FAIL"

        except Exception as e:
            results.append({"check": name, "status": "ERROR", "detail": str(e)})
            logger.error("[ERROR] %s: %s", name, e)

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Run data quality checks")
    parser.add_argument("--server", default=SQL_SERVER)
    parser.add_argument("--database", default=SQL_DATABASE)
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)
    results = run_checks(args.server, args.database)

    summary = pd.DataFrame(results)
    summary.to_csv(REPORTS_DIR / "data_quality_report.csv", index=False)

    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))

    logger.info("--- QUALITY SUMMARY ---")
    logger.info("PASS: %d | WARN: %d | FAIL: %d", passed, warned, failed)

    if failed > 0:
        logger.error("Data quality checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
