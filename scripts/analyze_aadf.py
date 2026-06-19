"""
AADF-based analyses: estimation quality, road category trends,
motorway vs A-road, HGV breakdown, coverage gaps, and more.

Usage:
    python scripts/analyze_aadf.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import AADF_FILE, COUNT_POINTS_FILE, REPORTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def analyze():
    REPORTS_DIR.mkdir(exist_ok=True)

    logger.info("Loading AADF data...")
    df = pd.read_csv(AADF_FILE, low_memory=False)
    logger.info("Loaded %d rows", len(df))

    # --- 1. Estimation Method Quality ---
    logger.info("Analyzing estimation method quality...")
    est_by_year = df.groupby(["year", "estimation_method"]).size().unstack(fill_value=0)
    est_by_year["total"] = est_by_year.sum(axis=1)
    if "Counted" in est_by_year.columns:
        est_by_year["counted_pct"] = (
            est_by_year["Counted"] / est_by_year["total"] * 100
        ).round(2)
    est_by_year.to_csv(REPORTS_DIR / "estimation_method_by_year.csv")

    est_detailed = df["estimation_method_detailed"].value_counts()
    est_detailed.to_frame("count").to_csv(
        REPORTS_DIR / "estimation_method_detailed.csv"
    )
    logger.info("Saved estimation_method_by_year.csv and estimation_method_detailed.csv")

    # --- 2. Motorway vs A-road Trends ---
    logger.info("Analyzing motorway vs A-road trends...")
    road_labels = {
        "TM": "Trunk Motorway",
        "PM": "Principal Motorway",
        "TA": "Trunk A-road",
        "PA": "Principal A-road",
        "M": "Minor",
        "MB": "B-road",
        "MCU": "C/Unclassified",
    }
    df["road_label"] = df["road_category"].map(road_labels)

    road_trend = df.groupby(["year", "road_category", "road_label"]).agg(
        total_motor=("all_motor_vehicles", "sum"),
        total_hgv=("all_HGVs", "sum"),
        total_cycles=("pedal_cycles", "sum"),
        count_points=("count_point_id", "nunique"),
        avg_flow=("all_motor_vehicles", "mean"),
    ).reset_index()
    road_trend["hgv_pct"] = (
        road_trend["total_hgv"] / road_trend["total_motor"] * 100
    ).round(2)
    road_trend.to_csv(REPORTS_DIR / "road_category_trends.csv", index=False)
    logger.info("Saved road_category_trends.csv")

    # --- 3. HGV Axle-Type Breakdown ---
    logger.info("Analyzing HGV axle types...")
    hgv_cols = [
        "HGVs_2_rigid_axle", "HGVs_3_rigid_axle", "HGVs_4_or_more_rigid_axle",
        "HGVs_3_or_4_articulated_axle", "HGVs_5_articulated_axle",
        "HGVs_6_articulated_axle",
    ]
    hgv_trend = df.groupby("year")[hgv_cols + ["all_HGVs"]].sum()
    for col in hgv_cols:
        short = col.replace("HGVs_", "").replace("_axle", "")
        hgv_trend[f"{short}_pct"] = (
            hgv_trend[col] / hgv_trend["all_HGVs"] * 100
        ).round(2)
    hgv_trend.to_csv(REPORTS_DIR / "hgv_axle_trends.csv")
    logger.info("Saved hgv_axle_trends.csv")

    # --- 4. Two-Wheeled & Bus Trends ---
    logger.info("Analyzing motorcycle and bus trends...")
    mode_trend = df.groupby("year").agg(
        motorcycles=("two_wheeled_motor_vehicles", "sum"),
        buses=("buses_and_coaches", "sum"),
        cars=("cars_and_taxis", "sum"),
        lgvs=("LGVs", "sum"),
        cycles=("pedal_cycles", "sum"),
        all_motor=("all_motor_vehicles", "sum"),
    ).reset_index()
    for col in ["motorcycles", "buses", "cars", "lgvs", "cycles"]:
        if col == "cycles":
            denom = mode_trend["all_motor"].astype(float) + mode_trend["cycles"].astype(float)
        else:
            denom = mode_trend["all_motor"].astype(float)
        mode_trend[f"{col}_pct"] = (mode_trend[col].astype(float) / denom * 100).round(3)
    mode_trend.to_csv(REPORTS_DIR / "vehicle_mode_trends.csv", index=False)
    logger.info("Saved vehicle_mode_trends.csv")

    # --- 5. Count Point Coverage Analysis ---
    logger.info("Analyzing count point coverage...")
    cp = pd.read_csv(COUNT_POINTS_FILE, low_memory=False)

    coverage = cp.groupby(["region_name", "road_category"]).agg(
        num_points=("count_point_id", "nunique"),
        total_link_km=("link_length_km", "sum"),
    ).reset_index()
    coverage["points_per_100km"] = (
        coverage["num_points"] / coverage["total_link_km"] * 100
    ).round(2)
    coverage = coverage.sort_values("points_per_100km")
    coverage.to_csv(REPORTS_DIR / "count_point_coverage.csv", index=False)
    logger.info("Saved count_point_coverage.csv")

    # Sparse regions (fewest points per km)
    region_coverage = cp.groupby("region_name").agg(
        num_points=("count_point_id", "nunique"),
        total_link_km=("link_length_km", "sum"),
    ).reset_index()
    region_coverage["density"] = (
        region_coverage["num_points"] / region_coverage["total_link_km"]
    ).round(4)
    region_coverage = region_coverage.sort_values("density")
    region_coverage.to_csv(REPORTS_DIR / "region_coverage_density.csv", index=False)
    logger.info("Saved region_coverage_density.csv")

    # --- 6. Directional Imbalance Score ---
    logger.info("Analyzing directional imbalance...")
    directed = df[df["direction_of_travel"] != "C"].copy()
    cp_dir = directed.groupby(
        ["count_point_id", "year", "road_name", "direction_of_travel"]
    )["all_motor_vehicles"].sum().reset_index()

    cp_pivot = cp_dir.pivot_table(
        index=["count_point_id", "year", "road_name"],
        columns="direction_of_travel",
        values="all_motor_vehicles",
        fill_value=0,
    ).reset_index()

    dir_cols = [c for c in cp_pivot.columns if c in ("N", "S", "E", "W")]
    if len(dir_cols) >= 2:
        cp_pivot["max_dir"] = cp_pivot[dir_cols].max(axis=1)
        cp_pivot["min_dir"] = cp_pivot[dir_cols].min(axis=1)
        cp_pivot["imbalance_ratio"] = (
            cp_pivot["max_dir"] / cp_pivot["min_dir"].replace(0, 1)
        ).round(2)

        top_imbalanced = cp_pivot[cp_pivot["year"] == 2023].nlargest(
            50, "imbalance_ratio"
        )
        top_imbalanced.to_csv(REPORTS_DIR / "directional_imbalance.csv", index=False)
        logger.info("Saved directional_imbalance.csv")

    # --- 7. Road Link Utilization (flow per km) ---
    logger.info("Analyzing road utilization...")
    df_2023 = df[df["year"] == 2023].copy()
    utilization = df_2023.groupby(
        ["count_point_id", "road_name", "road_category", "region_name", "link_length_km"]
    )["all_motor_vehicles"].sum().reset_index()
    utilization["flow_per_km"] = (
        utilization["all_motor_vehicles"] / utilization["link_length_km"].replace(0, float("nan"))
    ).round(0)
    utilization = utilization.dropna(subset=["flow_per_km"])
    utilization = utilization.nlargest(100, "flow_per_km")
    utilization.to_csv(REPORTS_DIR / "road_utilization_top100.csv", index=False)
    logger.info("Saved road_utilization_top100.csv")

    # --- Summary ---
    counted_pct = (
        (df["estimation_method"] == "Counted").sum() / len(df) * 100
    )
    logger.info("--- KEY FINDINGS ---")
    logger.info("Data quality: %.1f%% counted, %.1f%% estimated", counted_pct, 100 - counted_pct)
    logger.info("Road categories: TM=%d, PM=%d, TA=%d, PA=%d, Minor=%d",
        (df["road_category"] == "TM").sum(),
        (df["road_category"] == "PM").sum(),
        (df["road_category"] == "TA").sum(),
        (df["road_category"] == "PA").sum(),
        df["road_category"].isin(["M", "MB", "MCU"]).sum(),
    )
    logger.info("Coverage: %d unique count points across %d regions",
        cp["count_point_id"].nunique(),
        cp["region_name"].nunique(),
    )


if __name__ == "__main__":
    analyze()
