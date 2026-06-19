import logging
import sys
import time

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
from config.settings import SQLALCHEMY_URL, AADF_FILE, CHUNK_SIZE, SQL_INSERT_BATCH
from src.transform.clean import clean_aadf, validate_aadf

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


def load_fact_table():
    engine = create_engine(SQLALCHEMY_URL)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM FactTrafficFlowDirection"))
        logger.info("Cleared existing fact data")

    with engine.connect() as conn:
        date_map = dict(pd.read_sql("SELECT Year, DateKey FROM DimDate", conn).values)
        region_map = dict(pd.read_sql("SELECT RegionID, RegionKey FROM DimRegion", conn).values)
        la_map = dict(pd.read_sql(
            "SELECT LocalAuthorityID, LocalAuthorityKey FROM DimLocalAuthority", conn
        ).values)
        cp_map = dict(pd.read_sql(
            "SELECT CountPointID, CountPointKey FROM DimCountPoint", conn
        ).values)

    logger.info(
        "Dimension lookups: %d dates, %d regions, %d LAs, %d CPs",
        len(date_map), len(region_map), len(la_map), len(cp_map),
    )

    total_loaded = 0
    total_dropped = 0
    start_all = time.time()

    for i, chunk in enumerate(pd.read_csv(
        AADF_FILE, chunksize=CHUNK_SIZE, low_memory=False
    )):
        start_chunk = time.time()

        chunk = clean_aadf(chunk)

        chunk["DateKey"] = chunk["year"].map(date_map)
        chunk["RegionKey"] = chunk["region_id"].map(region_map)
        chunk["LocalAuthorityKey"] = chunk["local_authority_id"].map(la_map)
        chunk["CountPointKey"] = chunk["count_point_id"].map(cp_map)

        key_cols = ["DateKey", "CountPointKey", "LocalAuthorityKey", "RegionKey"]
        before = len(chunk)
        chunk = chunk.dropna(subset=key_cols)
        dropped = before - len(chunk)
        total_dropped += dropped

        source_cols = list(FACT_COLUMNS_MAP.keys())
        fact = chunk[source_cols].copy()
        fact.columns = list(FACT_COLUMNS_MAP.values())

        fact.to_sql(
            "FactTrafficFlowDirection", engine,
            if_exists="append", index=False, chunksize=SQL_INSERT_BATCH,
        )

        total_loaded += len(fact)
        elapsed = time.time() - start_chunk
        logger.info(
            "Chunk %d: %d rows loaded (%d dropped) | Total: %d | %.1fs",
            i + 1, len(fact), dropped, total_loaded, elapsed,
        )

    total_time = time.time() - start_all
    logger.info(
        "Fact table complete: %d rows loaded, %d dropped, %.0fs total",
        total_loaded, total_dropped, total_time,
    )


if __name__ == "__main__":
    load_fact_table()
