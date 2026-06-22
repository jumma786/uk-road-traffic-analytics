import logging
import pandas as pd

logger = logging.getLogger(__name__)

VEHICLE_COLS = [
    "pedal_cycles", "two_wheeled_motor_vehicles", "cars_and_taxis",
    "buses_and_coaches", "LGVs", "HGVs_2_rigid_axle", "HGVs_3_rigid_axle",
    "HGVs_4_or_more_rigid_axle", "HGVs_3_or_4_articulated_axle",
    "HGVs_5_articulated_axle", "HGVs_6_articulated_axle",
    "all_HGVs", "all_motor_vehicles",
]

REQUIRED_COLS = [
    "count_point_id", "year", "region_id", "local_authority_id",
    "direction_of_travel",
] + VEHICLE_COLS

VALID_DIRECTIONS = {"N", "S", "E", "W", "C"}
VALID_ROAD_CATEGORIES = {"TM", "PM", "TA", "PA", "M", "MB", "MCU"}


def validate_aadf(df: pd.DataFrame) -> dict:
    issues = {}

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        issues["missing_columns"] = missing

    for col in VEHICLE_COLS:
        if col in df.columns:
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                issues[f"negative_{col}"] = int(neg_count)

    if "direction_of_travel" in df.columns:
        bad_dirs = set(df["direction_of_travel"].dropna().unique()) - VALID_DIRECTIONS
        if bad_dirs:
            issues["invalid_directions"] = list(bad_dirs)

    if "road_category" in df.columns:
        bad_cats = set(df["road_category"].dropna().unique()) - VALID_ROAD_CATEGORIES
        if bad_cats:
            issues["invalid_road_categories"] = list(bad_cats)

    present_required = [c for c in REQUIRED_COLS if c in df.columns]
    if present_required:
        null_counts = df[present_required].isnull().sum()
        nulls = null_counts[null_counts > 0].to_dict()
        if nulls:
            issues["null_values"] = {k: int(v) for k, v in nulls.items()}

    return issues


def clean_aadf(df: pd.DataFrame) -> pd.DataFrame:
    initial_rows = len(df)

    for col in VEHICLE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            df.loc[df[col] < 0, col] = 0

    key_cols = ["count_point_id", "year", "region_id", "local_authority_id"]
    df = df.dropna(subset=key_cols)

    if "direction_of_travel" in df.columns:
        df = df[df["direction_of_travel"].isin(VALID_DIRECTIONS)]

    if "year" in df.columns:
        df = df[(df["year"] >= 2000) & (df["year"] <= 2025)]

    dropped = initial_rows - len(df)
    if dropped > 0:
        logger.info("Cleaned %d rows (dropped %d invalid)", len(df), dropped)

    return df
