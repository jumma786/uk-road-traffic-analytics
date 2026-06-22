"""
Incremental fact table loader. Only loads data for years not already present.

Usage:
    python src/load/load_incremental.py
    python src/load/load_incremental.py --year 2024
"""

import argparse
import logging
import sys
import time

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
from config.settings import SQLALCHEMY_URL, AADF_FILE, CHUNK_SIZE, SQL_INSERT_BATCH
from src.transform.clean import clean_aadf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FACT_COLUMNS_MAP = {
    "DateKey": "DateKey",
    "CountPointKey": "CountPointKey",
    "LocalAuthorityKey": "LocalAuthorityKey",
    "RegionKey": "RegionKey",
    "direction_of_travel": "DirectionOfTravel",
    "pedal_cycles": "PedalCycles",
    "two_wheeled_motor_vehicles": "TwoWheeledMotorVehicles",
    "cars_and_taxis": "CarsAndTaxis",
    "buses_and_coaches": "BusesAndCoaches",
    "LGVs": "LGVs",
    "HGVs_2_rigid_axle": "HGVs2RigidAxle",
    "HGVs_3_rigid_axle": "HGVs3RigidAxle",
    "HGVs_4_or_more_rigid_axle": "HGVs4OrMoreRigidAxle",
    "HGVs_3_or_4_articulated_axle": "HGVs3Or4ArticulatedAxle",
    "HGVs_5_articulated_axle": "HGVs5ArticulatedAxle",
    "HGVs_6_articulated_axle": "HGVs6ArticulatedAxle",
    "all_HGVs": "AllHGVs",
    "all_motor_vehicles": "AllMotorVehicles",
}


def get_loaded_years(engine) -> set[int]:
    with engine.connect() as conn:
        df = pd.read_sql(text(
            "SELECT DISTINCT d.Year FROM FactTrafficFlowDirection f "
            "JOIN DimDate d ON f.DateKey = d.DateKey"
        ), conn)
    return set(df["Year"].tolist())


def load_incremental(target_years: set[int] | None = None):
    engine = create_engine(SQLALCHEMY_URL)
    loaded_years = get_loaded_years(engine)

    with engine.connect() as conn:
        date_map = dict(pd.read_sql("SELECT Year, DateKey FROM DimDate", conn).values)
        region_map = dict(pd.read_sql("SELECT RegionID, RegionKey FROM DimRegion", conn).values)
        la_map = dict(pd.read_sql("SELECT LocalAuthorityID, LocalAuthorityKey FROM DimLocalAuthority", conn).values)
        cp_map = dict(pd.read_sql("SELECT CountPointID, CountPointKey FROM DimCountPoint", conn).values)

    if target_years:
        years_to_load = target_years - loaded_years
    else:
        all_csv_years = set(pd.read_csv(AADF_FILE, usecols=["year"])["year"].unique())
        years_to_load = all_csv_years - loaded_years

    if not years_to_load:
        logger.info("No new years to load. All data is current.")
        return

    logger.info("Loading years: %s", sorted(years_to_load))

    total_loaded = 0
    start = time.time()

    for i, chunk in enumerate(pd.read_csv(AADF_FILE, chunksize=CHUNK_SIZE, low_memory=False)):
        chunk = chunk[chunk["year"].isin(years_to_load)]
        if chunk.empty:
            continue

        chunk = clean_aadf(chunk)
        chunk["DateKey"] = chunk["year"].map(date_map)
        chunk["RegionKey"] = chunk["region_id"].map(region_map)
        chunk["LocalAuthorityKey"] = chunk["local_authority_id"].map(la_map)
        chunk["CountPointKey"] = chunk["count_point_id"].map(cp_map)

        chunk = chunk.dropna(subset=["DateKey", "CountPointKey", "LocalAuthorityKey", "RegionKey"])

        source_cols = list(FACT_COLUMNS_MAP.keys())
        fact = chunk[source_cols].copy()
        fact.columns = list(FACT_COLUMNS_MAP.values())

        fact.to_sql(
            "FactTrafficFlowDirection", engine,
            if_exists="append", index=False, chunksize=SQL_INSERT_BATCH,
        )
        total_loaded += len(fact)

        if (i + 1) % 20 == 0:
            logger.info("Processed %d chunks, %d rows loaded so far", i + 1, total_loaded)

    elapsed = time.time() - start
    logger.info("Incremental load complete: %d rows in %.0fs", total_loaded, elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incremental fact table loader")
    parser.add_argument("--year", type=int, help="Load a specific year")
    args = parser.parse_args()

    target = {args.year} if args.year else None
    load_incremental(target)
