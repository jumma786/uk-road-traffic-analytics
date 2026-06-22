"""
REST API to serve traffic analytics data.

Usage:
    uvicorn src.api.app:app --reload
    python -m src.api.app
"""

import sys
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

app = FastAPI(
    title="UK Road Traffic Analytics API",
    version="1.0.0",
    description="REST API for UK DfT road traffic data warehouse",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_engine():
    from config.settings import SQLALCHEMY_URL
    from sqlalchemy import create_engine
    return create_engine(SQLALCHEMY_URL)


def _query(sql: str, params: dict | None = None) -> list[dict]:
    import pandas as pd
    from sqlalchemy import text
    engine = _get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/tables")
def table_counts():
    return _query("""
        SELECT 'DimDate' AS name, COUNT(*) AS rows FROM DimDate
        UNION ALL SELECT 'DimRegion', COUNT(*) FROM DimRegion
        UNION ALL SELECT 'DimLocalAuthority', COUNT(*) FROM DimLocalAuthority
        UNION ALL SELECT 'DimCountPoint', COUNT(*) FROM DimCountPoint
        UNION ALL SELECT 'FactTrafficFlowDirection', COUNT(*) FROM FactTrafficFlowDirection
    """)


@app.get("/api/regions")
def regions():
    return _query("SELECT RegionKey, RegionID, RegionName, RegionONSCode FROM DimRegion ORDER BY RegionName")


@app.get("/api/traffic/yearly")
def yearly_traffic():
    return _query("""
        SELECT d.Year, SUM(f.AllMotorVehicles) AS TotalMotor,
               SUM(f.AllHGVs) AS TotalHGV, SUM(f.PedalCycles) AS TotalCycles
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year ORDER BY d.Year
    """)


@app.get("/api/traffic/by-region")
def traffic_by_region(year: int = Query(default=2023)):
    return _query("""
        SELECT r.RegionName, SUM(f.AllMotorVehicles) AS TotalMotor,
               SUM(f.AllHGVs) AS TotalHGV
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = :year
        GROUP BY r.RegionName ORDER BY TotalMotor DESC
    """, {"year": year})


@app.get("/api/traffic/top-roads")
def top_roads(year: int = Query(default=2023), limit: int = Query(default=10, le=100)):
    return _query(f"""
        SELECT TOP {limit} cp.RoadName, cp.RoadCategory,
               SUM(f.AllMotorVehicles) AS TotalTraffic
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = :year
        GROUP BY cp.RoadName, cp.RoadCategory
        ORDER BY TotalTraffic DESC
    """, {"year": year})


@app.get("/api/traffic/vehicle-mix")
def vehicle_mix(year: int = Query(default=2023)):
    return _query("""
        SELECT r.RegionName,
               SUM(f.CarsAndTaxis) AS Cars,
               SUM(f.LGVs) AS LGVs,
               SUM(f.AllHGVs) AS HGVs,
               SUM(f.BusesAndCoaches) AS Buses,
               SUM(f.PedalCycles) AS Cycles,
               SUM(f.TwoWheeledMotorVehicles) AS Motorcycles
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = :year
        GROUP BY r.RegionName ORDER BY r.RegionName
    """, {"year": year})


@app.get("/api/traffic/geospatial")
def geospatial(year: int = Query(default=2023), min_traffic: int = Query(default=50000)):
    return _query("""
        SELECT cp.Latitude, cp.Longitude, cp.RoadName, r.RegionName,
               SUM(f.AllMotorVehicles) AS TotalTraffic
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = :year
        GROUP BY cp.Latitude, cp.Longitude, cp.RoadName, r.RegionName
        HAVING SUM(f.AllMotorVehicles) > :min_traffic
        ORDER BY TotalTraffic DESC
    """, {"year": year, "min_traffic": min_traffic})


if __name__ == "__main__":
    import uvicorn
    import os
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run("src.api.app:app", host=host, port=port, reload=True)
