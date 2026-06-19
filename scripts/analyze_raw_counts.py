"""
Analyze raw hourly traffic counts (5.3M rows) for time-of-day,
day-of-week, and seasonal patterns. Processes in chunks to manage memory.

Usage:
    python scripts/analyze_raw_counts.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_COUNTS_FILE, REPORTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

VEHICLE_COLS = [
    "pedal_cycles", "two_wheeled_motor_vehicles", "cars_and_taxis",
    "buses_and_coaches", "LGVs", "all_HGVs", "all_motor_vehicles",
]


def analyze():
    REPORTS_DIR.mkdir(exist_ok=True)

    hourly_agg = None
    dow_agg = None
    monthly_agg = None
    yearly_hourly_agg = None
    road_hourly_agg = None

    logger.info("Processing raw counts from %s...", RAW_COUNTS_FILE.name)

    for i, chunk in enumerate(pd.read_csv(
        RAW_COUNTS_FILE, chunksize=100_000, low_memory=False,
        parse_dates=["count_date"],
    )):
        chunk["day_of_week"] = chunk["count_date"].dt.dayofweek
        chunk["day_name"] = chunk["count_date"].dt.strftime("%A")
        chunk["month"] = chunk["count_date"].dt.month
        chunk["is_weekend"] = chunk["day_of_week"].isin([5, 6]).astype(int)

        # 1. Hourly pattern
        h = chunk.groupby("hour")[VEHICLE_COLS].sum()
        hourly_agg = h if hourly_agg is None else hourly_agg.add(h, fill_value=0)

        # 2. Day-of-week pattern
        d = chunk.groupby(["day_of_week", "day_name"])[VEHICLE_COLS].sum()
        dow_agg = d if dow_agg is None else dow_agg.add(d, fill_value=0)

        # 3. Monthly/seasonal pattern
        m = chunk.groupby("month")[VEHICLE_COLS].sum()
        monthly_agg = m if monthly_agg is None else monthly_agg.add(m, fill_value=0)

        # 4. Year × hour heatmap
        yh = chunk.groupby(["year", "hour"])[["all_motor_vehicles"]].sum()
        yearly_hourly_agg = yh if yearly_hourly_agg is None else yearly_hourly_agg.add(yh, fill_value=0)

        # 5. Road category × hour
        rh = chunk.groupby(["road_category", "hour"])[["all_motor_vehicles"]].sum()
        road_hourly_agg = rh if road_hourly_agg is None else road_hourly_agg.add(rh, fill_value=0)

        if (i + 1) % 10 == 0:
            logger.info("Processed %d chunks (%dK rows)", i + 1, (i + 1) * 100)

    logger.info("Aggregation complete. Saving reports...")

    # Save hourly pattern
    hourly = hourly_agg.reset_index()
    hourly["hour_label"] = hourly["hour"].apply(lambda h: f"{h:02d}:00-{h+1:02d}:00")
    hourly.to_csv(REPORTS_DIR / "peak_hour_pattern.csv", index=False)
    logger.info("Saved peak_hour_pattern.csv")

    am_peak = hourly[hourly["hour"].isin([7, 8, 9])]["all_motor_vehicles"].sum()
    pm_peak = hourly[hourly["hour"].isin([16, 17, 18])]["all_motor_vehicles"].sum()
    total = hourly["all_motor_vehicles"].sum()
    logger.info(
        "AM peak (7-10): %.1f%% | PM peak (16-19): %.1f%%",
        am_peak / total * 100, pm_peak / total * 100,
    )

    # Save day-of-week pattern
    dow = dow_agg.reset_index()
    dow = dow.sort_values("day_of_week")
    dow.to_csv(REPORTS_DIR / "day_of_week_pattern.csv", index=False)
    logger.info("Saved day_of_week_pattern.csv")

    # Save monthly/seasonal pattern
    monthly = monthly_agg.reset_index()
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    monthly["month_name"] = monthly["month"].map(month_names)
    monthly.to_csv(REPORTS_DIR / "seasonal_pattern.csv", index=False)
    logger.info("Saved seasonal_pattern.csv")

    # Save year × hour heatmap
    yh_pivot = yearly_hourly_agg.reset_index().pivot(
        index="year", columns="hour", values="all_motor_vehicles"
    ).fillna(0)
    yh_pivot.to_csv(REPORTS_DIR / "year_hour_heatmap.csv")
    logger.info("Saved year_hour_heatmap.csv")

    # Save road category × hour
    rh_pivot = road_hourly_agg.reset_index().pivot(
        index="road_category", columns="hour", values="all_motor_vehicles"
    ).fillna(0)
    rh_pivot.to_csv(REPORTS_DIR / "road_category_hourly.csv")
    logger.info("Saved road_category_hourly.csv")

    # Print summary
    peak_hour = hourly.loc[hourly["all_motor_vehicles"].idxmax()]
    quiet_hour = hourly.loc[hourly["all_motor_vehicles"].idxmin()]
    busiest_day = dow.loc[dow["all_motor_vehicles"].idxmax()]
    quietest_day = dow.loc[dow["all_motor_vehicles"].idxmin()]
    busiest_month = monthly.loc[monthly["all_motor_vehicles"].idxmax()]

    logger.info("--- KEY FINDINGS ---")
    logger.info("Peak hour: %s (%s vehicles)", peak_hour["hour_label"], f"{peak_hour['all_motor_vehicles']:,.0f}")
    logger.info("Quietest hour: %s (%s vehicles)", quiet_hour["hour_label"], f"{quiet_hour['all_motor_vehicles']:,.0f}")
    logger.info("Busiest day: %s", busiest_day["day_name"])
    logger.info("Quietest day: %s", quietest_day["day_name"])
    logger.info("Busiest month: %s", busiest_month["month_name"])


if __name__ == "__main__":
    analyze()
