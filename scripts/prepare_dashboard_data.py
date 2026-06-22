"""
Pre-aggregate AADF data into small CSVs for the cloud dashboard.
These files are small enough to commit to git and deploy to Streamlit Cloud.

Usage:
    python scripts/prepare_dashboard_data.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import AADF_FILE, COUNT_POINTS_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "dashboard"


def prepare():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading AADF data...")
    df = pd.read_csv(AADF_FILE, low_memory=False)
    cp = pd.read_csv(COUNT_POINTS_FILE, low_memory=False)
    logger.info("Loaded %d AADF rows, %d count points", len(df), len(cp))

    # 1. Yearly totals
    yearly = df.groupby("year").agg(
        TotalMotor=("all_motor_vehicles", "sum"),
        TotalHGV=("all_HGVs", "sum"),
        TotalCycles=("pedal_cycles", "sum"),
        TotalCars=("cars_and_taxis", "sum"),
        TotalLGVs=("LGVs", "sum"),
        TotalBuses=("buses_and_coaches", "sum"),
        TotalMotorcycles=("two_wheeled_motor_vehicles", "sum"),
        CountPoints=("count_point_id", "nunique"),
    ).reset_index()
    yearly.columns = ["Year", "TotalMotor", "TotalHGV", "TotalCycles",
                       "TotalCars", "TotalLGVs", "TotalBuses", "TotalMotorcycles", "CountPoints"]
    yearly.to_csv(OUT_DIR / "yearly_totals.csv", index=False)
    logger.info("Saved yearly_totals.csv (%d rows)", len(yearly))

    # 2. Regional by year
    regional = df.groupby(["year", "region_name"]).agg(
        TotalMotor=("all_motor_vehicles", "sum"),
        TotalHGV=("all_HGVs", "sum"),
        TotalCars=("cars_and_taxis", "sum"),
        TotalLGVs=("LGVs", "sum"),
        TotalBuses=("buses_and_coaches", "sum"),
        TotalMotorcycles=("two_wheeled_motor_vehicles", "sum"),
        TotalCycles=("pedal_cycles", "sum"),
        CountPoints=("count_point_id", "nunique"),
    ).reset_index()
    regional.columns = ["Year", "RegionName", "TotalMotor", "TotalHGV",
                         "TotalCars", "TotalLGVs", "TotalBuses", "TotalMotorcycles",
                         "TotalCycles", "CountPoints"]
    regional.to_csv(OUT_DIR / "regional_by_year.csv", index=False)
    logger.info("Saved regional_by_year.csv (%d rows)", len(regional))

    # 3. Top roads by year (top 50 per year)
    road_yearly = df.groupby(["year", "road_name", "road_category"]).agg(
        TotalTraffic=("all_motor_vehicles", "sum"),
    ).reset_index()
    top_roads_list = []
    for year, group in road_yearly.groupby("year"):
        top_roads_list.append(group.nlargest(50, "TotalTraffic"))
    top_roads = pd.concat(top_roads_list, ignore_index=True)
    top_roads.columns = ["Year", "RoadName", "RoadCategory", "TotalTraffic"]
    top_roads.to_csv(OUT_DIR / "top_roads_by_year.csv", index=False)
    logger.info("Saved top_roads_by_year.csv (%d rows)", len(top_roads))

    # 4. Geospatial hotspots (latest year, aggregated by count point)
    latest_year = df["year"].max()
    geo_df = df[df["year"] == latest_year].copy()
    geo_agg = geo_df.groupby(["count_point_id", "road_name", "region_name"]).agg(
        TotalTraffic=("all_motor_vehicles", "sum"),
        Latitude=("latitude", "first"),
        Longitude=("longitude", "first"),
    ).reset_index()
    geo_agg = geo_agg[geo_agg["TotalTraffic"] > 10000]
    geo_agg.columns = ["CountPointID", "RoadName", "RegionName",
                        "TotalTraffic", "Latitude", "Longitude"]
    geo_agg.to_csv(OUT_DIR / "geospatial_hotspots.csv", index=False)
    logger.info("Saved geospatial_hotspots.csv (%d rows)", len(geo_agg))

    # 5. Vehicle mix by region (latest year)
    mix = df[df["year"] == latest_year].groupby("region_name").agg(
        Cars=("cars_and_taxis", "sum"),
        LGVs=("LGVs", "sum"),
        HGVs=("all_HGVs", "sum"),
        Buses=("buses_and_coaches", "sum"),
        Motorcycles=("two_wheeled_motor_vehicles", "sum"),
        Cycles=("pedal_cycles", "sum"),
    ).reset_index()
    mix.columns = ["RegionName", "Cars", "LGVs", "HGVs", "Buses", "Motorcycles", "Cycles"]
    mix.to_csv(OUT_DIR / "vehicle_mix.csv", index=False)
    logger.info("Saved vehicle_mix.csv (%d rows)", len(mix))

    # 6. Road category distribution
    road_cat = df.groupby(["year", "road_category"]).agg(
        TotalTraffic=("all_motor_vehicles", "sum"),
        CountPoints=("count_point_id", "nunique"),
    ).reset_index()
    road_cat.columns = ["Year", "RoadCategory", "TotalTraffic", "CountPoints"]
    road_cat.to_csv(OUT_DIR / "road_category_by_year.csv", index=False)
    logger.info("Saved road_category_by_year.csv (%d rows)", len(road_cat))

    total_size = sum(f.stat().st_size for f in OUT_DIR.glob("*.csv")) / 1024
    logger.info("Done. Total dashboard data: %.0f KB in %s/", total_size, OUT_DIR.name)


if __name__ == "__main__":
    prepare()
