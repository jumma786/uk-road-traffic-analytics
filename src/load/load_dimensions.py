import logging
import sys

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
from config.settings import SQLALCHEMY_URL, COUNT_POINTS_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_dimensions():
    engine = create_engine(SQLALCHEMY_URL)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM FactTrafficFlowDirection"))
        conn.execute(text("DELETE FROM DimCountPoint"))
        conn.execute(text("DELETE FROM DimLocalAuthority"))
        conn.execute(text("DELETE FROM DimRegion"))
        conn.execute(text("DELETE FROM DimDate"))
        logger.info("Cleared existing dimension data")

    # 1. DimDate — year-grain only (one row per year, DateKey = year)
    logger.info("Loading DimDate...")
    years = range(2000, 2026)
    dim_date = pd.DataFrame({
        "DateKey": list(years),
        "FullDate": [pd.Timestamp(y, 1, 1) for y in years],
        "Year": list(years),
        "Quarter": [1] * len(years),
        "Month": [1] * len(years),
        "MonthName": ["January"] * len(years),
        "Day": [1] * len(years),
        "DayOfWeek": [pd.Timestamp(y, 1, 1).dayofweek + 1 for y in years],
        "DayName": [pd.Timestamp(y, 1, 1).strftime("%A") for y in years],
        "IsWeekend": [0] * len(years),
        "FiscalYear": list(years),
    })
    dim_date.to_sql("DimDate", engine, if_exists="append", index=False)
    logger.info("Loaded %d years into DimDate", len(dim_date))

    # 2. DimRegion
    logger.info("Loading DimRegion...")
    df = pd.read_csv(COUNT_POINTS_FILE, usecols=["region_id", "region_name", "region_ons_code"])
    dim_region = df.drop_duplicates().rename(columns={
        "region_id": "RegionID",
        "region_name": "RegionName",
        "region_ons_code": "RegionONSCode",
    })
    dim_region.to_sql("DimRegion", engine, if_exists="append", index=False)
    logger.info("Loaded %d regions", len(dim_region))

    # 3. DimLocalAuthority
    logger.info("Loading DimLocalAuthority...")
    df = pd.read_csv(COUNT_POINTS_FILE, usecols=[
        "local_authority_id", "local_authority_name", "local_authority_code", "region_id"
    ])
    dim_la = df.drop_duplicates().rename(columns={
        "local_authority_id": "LocalAuthorityID",
        "local_authority_name": "LocalAuthorityName",
        "local_authority_code": "LocalAuthorityCode",
        "region_id": "RegionID",
    })

    with engine.connect() as conn:
        region_map = pd.read_sql("SELECT RegionKey, RegionID FROM DimRegion", conn)

    dim_la = dim_la.merge(region_map, on="RegionID", how="left")
    dim_la = dim_la[["LocalAuthorityID", "RegionKey", "LocalAuthorityName", "LocalAuthorityCode"]]
    dim_la.to_sql("DimLocalAuthority", engine, if_exists="append", index=False)
    logger.info("Loaded %d local authorities", len(dim_la))

    # 4. DimCountPoint
    logger.info("Loading DimCountPoint...")
    df = pd.read_csv(COUNT_POINTS_FILE, low_memory=False)
    dim_cp = df[[
        "count_point_id", "road_name", "road_category", "road_type",
        "latitude", "longitude", "link_length_km"
    ]].drop_duplicates("count_point_id").rename(columns={
        "count_point_id": "CountPointID",
        "road_name": "RoadName",
        "road_category": "RoadCategory",
        "road_type": "RoadType",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "link_length_km": "LinkLengthKm",
    })
    dim_cp.to_sql("DimCountPoint", engine, if_exists="append", index=False)
    logger.info("Loaded %d count points", len(dim_cp))

    logger.info("All dimensions loaded successfully")


if __name__ == "__main__":
    load_dimensions()
