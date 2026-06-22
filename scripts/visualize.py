"""
Generate static charts from CSV report data.
Reads from reports/ and saves PNG charts to reports/charts/.

Usage:
    python scripts/visualize.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import REPORTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHARTS_DIR = REPORTS_DIR / "charts"


def plot_yoy_growth():
    path = REPORTS_DIR / "yoy_growth_trend.csv"
    if not path.exists():
        logger.warning("Skipping YoY growth chart: %s not found", path.name)
        return
    df = pd.read_csv(path)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(df["Year"], df["TotalTraffic"] / 1e9, color="#2196F3", alpha=0.7)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Total Traffic (Billions)")
    ax1.set_title("UK Road Traffic: Year-over-Year Trend")
    if "YoY_GrowthPct" in df.columns:
        ax2 = ax1.twinx()
        valid = df.dropna(subset=["YoY_GrowthPct"])
        ax2.plot(valid["Year"], valid["YoY_GrowthPct"], "r-o", linewidth=2)
        ax2.set_ylabel("YoY Growth %", color="red")
        ax2.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "yoy_growth_trend.png", dpi=150)
    plt.close()
    logger.info("Saved yoy_growth_trend.png")


def plot_regional_summary():
    path = REPORTS_DIR / "regional_traffic_summary.csv"
    if not path.exists():
        logger.warning("Skipping regional chart: %s not found", path.name)
        return
    df = pd.read_csv(path).sort_values("TotalMotorVehicles", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(df["RegionName"], df["TotalMotorVehicles"] / 1e6, color="#4CAF50")
    ax.set_xlabel("Total Motor Vehicles (Millions)")
    ax.set_title("Traffic by Region (2023)")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "regional_traffic.png", dpi=150)
    plt.close()
    logger.info("Saved regional_traffic.png")


def plot_vehicle_mix():
    path = REPORTS_DIR / "hgv_passenger_mix.csv"
    if not path.exists():
        logger.warning("Skipping vehicle mix chart: %s not found", path.name)
        return
    df = pd.read_csv(path).sort_values("HGV_Pct", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(df["RegionName"], df["HGV_Pct"], color="#FF9800")
    ax.set_xlabel("HGV Share (%)")
    ax.set_title("HGV vs Passenger Vehicle Mix by Region")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "hgv_passenger_mix.png", dpi=150)
    plt.close()
    logger.info("Saved hgv_passenger_mix.png")


def plot_covid_impact():
    path = REPORTS_DIR / "covid_impact.csv"
    if not path.exists():
        logger.warning("Skipping COVID chart: %s not found", path.name)
        return
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(12, 6))
    cols = ["Cars", "LGVs", "HGVs", "Buses", "Cycles"]
    available = [c for c in cols if c in df.columns]
    for col in available:
        ax.plot(df["Year"], df[col] / 1e6, "-o", label=col, linewidth=2)
    ax.set_xlabel("Year")
    ax.set_ylabel("Total AADF (Millions)")
    ax.set_title("COVID-19 Impact on UK Traffic by Vehicle Type")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "covid_impact.png", dpi=150)
    plt.close()
    logger.info("Saved covid_impact.png")


def plot_cycling_trends():
    path = REPORTS_DIR / "cycling_trends.csv"
    if not path.exists():
        logger.warning("Skipping cycling chart: %s not found", path.name)
        return
    df = pd.read_csv(path)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(df["Year"], df["TotalCycles"] / 1e3, color="#00BCD4", alpha=0.7)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Total Pedal Cycles (Thousands)")
    ax1.set_title("UK Cycling Trends Over Time")
    if "CycleSharePct" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["Year"], df["CycleSharePct"], "g-o", linewidth=2)
        ax2.set_ylabel("Cycle Mode Share %", color="green")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "cycling_trends.png", dpi=150)
    plt.close()
    logger.info("Saved cycling_trends.png")


def plot_road_category():
    path = REPORTS_DIR / "road_category_distribution.csv"
    if not path.exists():
        logger.warning("Skipping road category chart: %s not found", path.name)
        return
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        df["TotalTraffic"], labels=df["RoadCategory"],
        autopct="%1.1f%%", startangle=140,
    )
    ax.set_title("Traffic Distribution by Road Category")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "road_category_pie.png", dpi=150)
    plt.close()
    logger.info("Saved road_category_pie.png")


def plot_lgv_trend():
    path = REPORTS_DIR / "lgv_ecommerce_trend.csv"
    if not path.exists():
        logger.warning("Skipping LGV chart: %s not found", path.name)
        return
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(df["Year"], df["LGV_SharePct"], alpha=0.3, color="#9C27B0")
    ax.plot(df["Year"], df["LGV_SharePct"], "-o", color="#9C27B0", linewidth=2)
    ax.set_xlabel("Year")
    ax.set_ylabel("LGV Share of Motor Vehicles (%)")
    ax.set_title("LGV Growth Trend (E-Commerce Indicator)")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "lgv_ecommerce_trend.png", dpi=150)
    plt.close()
    logger.info("Saved lgv_ecommerce_trend.png")


def main():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Generating charts from reports/ ...")

    plot_yoy_growth()
    plot_regional_summary()
    plot_vehicle_mix()
    plot_covid_impact()
    plot_cycling_trends()
    plot_road_category()
    plot_lgv_trend()

    logger.info("Done. Charts saved to %s/", CHARTS_DIR)


if __name__ == "__main__":
    main()
