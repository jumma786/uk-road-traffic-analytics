"""
Streamlit dashboard for UK Road Traffic Analytics.

Usage:
    streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

st.set_page_config(page_title="UK Road Traffic Analytics", layout="wide")
st.title("UK Road Traffic Analytics Dashboard")


@st.cache_resource
def get_engine():
    from config.settings import SQLALCHEMY_URL
    from sqlalchemy import create_engine
    return create_engine(SQLALCHEMY_URL)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


try:
    engine = get_engine()
    years_df = query("SELECT DISTINCT d.Year FROM FactTrafficFlowDirection f JOIN DimDate d ON f.DateKey = d.DateKey ORDER BY d.Year")
    available_years = years_df["Year"].tolist()
except Exception as e:
    st.error(f"Cannot connect to database: {e}")
    st.info("Configure SQL_SERVER and SQL_DATABASE in your .env file.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Regional", "Vehicle Mix", "Trends", "Map",
])

with tab1:
    st.header("Traffic Overview")

    yearly = query("""
        SELECT d.Year,
               SUM(f.AllMotorVehicles) AS TotalMotor,
               SUM(f.AllHGVs) AS TotalHGV,
               SUM(f.PedalCycles) AS TotalCycles,
               COUNT(DISTINCT f.CountPointKey) AS CountPoints
        FROM FactTrafficFlowDirection f
        JOIN DimDate d ON f.DateKey = d.DateKey
        GROUP BY d.Year ORDER BY d.Year
    """)

    latest = yearly.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Year", int(latest["Year"]))
    col2.metric("Motor Vehicles", f"{latest['TotalMotor'] / 1e6:.1f}M")
    col3.metric("HGVs", f"{latest['TotalHGV'] / 1e6:.1f}M")
    col4.metric("Count Points", f"{latest['CountPoints']:,}")

    fig = px.bar(
        yearly, x="Year", y="TotalMotor",
        title="Total Motor Vehicle AADF by Year",
        labels={"TotalMotor": "Total AADF"},
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Regional Analysis")
    selected_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1, key="reg_year")

    regional = query(f"""
        SELECT r.RegionName,
               SUM(f.AllMotorVehicles) AS TotalMotor,
               SUM(f.AllHGVs) AS TotalHGV,
               COUNT(DISTINCT f.CountPointKey) AS CountPoints
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = {selected_year}
        GROUP BY r.RegionName
        ORDER BY TotalMotor DESC
    """)

    fig = px.bar(
        regional, x="TotalMotor", y="RegionName", orientation="h",
        title=f"Traffic by Region ({selected_year})",
        labels={"TotalMotor": "Total AADF", "RegionName": "Region"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(regional, use_container_width=True)

with tab3:
    st.header("Vehicle Type Mix")
    mix_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1, key="mix_year")

    mix = query(f"""
        SELECT r.RegionName,
               SUM(f.CarsAndTaxis) AS Cars,
               SUM(f.LGVs) AS LGVs,
               SUM(f.AllHGVs) AS HGVs,
               SUM(f.BusesAndCoaches) AS Buses,
               SUM(f.TwoWheeledMotorVehicles) AS Motorcycles,
               SUM(f.PedalCycles) AS Cycles
        FROM FactTrafficFlowDirection f
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = {mix_year}
        GROUP BY r.RegionName
    """)

    totals = mix[["Cars", "LGVs", "HGVs", "Buses", "Motorcycles", "Cycles"]].sum()
    fig = px.pie(
        values=totals.values, names=totals.index,
        title=f"National Vehicle Mix ({mix_year})",
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        mix.melt(id_vars="RegionName", value_vars=["Cars", "LGVs", "HGVs", "Buses"]),
        x="RegionName", y="value", color="variable", barmode="group",
        title="Vehicle Types by Region",
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.header("Traffic Trends")

    trend_type = st.radio("Trend", ["COVID Impact", "Cycling", "LGV Growth", "Bus Decline"], horizontal=True)

    if trend_type == "COVID Impact":
        covid = query("""
            SELECT d.Year,
                   SUM(f.CarsAndTaxis) AS Cars,
                   SUM(f.LGVs) AS LGVs,
                   SUM(f.AllHGVs) AS HGVs,
                   SUM(f.BusesAndCoaches) AS Buses,
                   SUM(f.PedalCycles) AS Cycles
            FROM FactTrafficFlowDirection f
            JOIN DimDate d ON f.DateKey = d.DateKey
            WHERE d.Year BETWEEN 2017 AND 2023
            GROUP BY d.Year ORDER BY d.Year
        """)
        melted = covid.melt(id_vars="Year", var_name="Vehicle", value_name="AADF")
        fig = px.line(melted, x="Year", y="AADF", color="Vehicle", title="COVID Impact by Vehicle Type", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    elif trend_type == "Cycling":
        cycling = query("""
            SELECT d.Year, SUM(f.PedalCycles) AS TotalCycles,
                   ROUND(SUM(f.PedalCycles) * 100.0 /
                       NULLIF(SUM(f.AllMotorVehicles) + SUM(f.PedalCycles), 0), 4) AS CycleShare
            FROM FactTrafficFlowDirection f
            JOIN DimDate d ON f.DateKey = d.DateKey
            GROUP BY d.Year ORDER BY d.Year
        """)
        fig = px.line(cycling, x="Year", y="TotalCycles", title="Pedal Cycle AADF Over Time", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    elif trend_type == "LGV Growth":
        lgv = query("""
            SELECT d.Year, SUM(f.LGVs) AS TotalLGVs,
                   ROUND(SUM(f.LGVs) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 2) AS LGV_Share
            FROM FactTrafficFlowDirection f
            JOIN DimDate d ON f.DateKey = d.DateKey
            GROUP BY d.Year ORDER BY d.Year
        """)
        fig = px.area(lgv, x="Year", y="LGV_Share", title="LGV Share of Traffic (E-Commerce Indicator)")
        st.plotly_chart(fig, use_container_width=True)

    elif trend_type == "Bus Decline":
        bus = query("""
            SELECT d.Year, SUM(f.BusesAndCoaches) AS TotalBuses,
                   ROUND(SUM(f.BusesAndCoaches) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 3) AS BusShare
            FROM FactTrafficFlowDirection f
            JOIN DimDate d ON f.DateKey = d.DateKey
            GROUP BY d.Year ORDER BY d.Year
        """)
        fig = px.line(bus, x="Year", y="BusShare", title="Bus & Coach Share Over Time", markers=True)
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.header("Traffic Hotspot Map")
    map_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1, key="map_year")
    min_traffic = st.slider("Minimum Traffic Threshold", 10000, 500000, 50000, step=10000)

    geo = query(f"""
        SELECT cp.Latitude, cp.Longitude, cp.RoadName, r.RegionName,
               SUM(f.AllMotorVehicles) AS TotalTraffic
        FROM FactTrafficFlowDirection f
        JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
        JOIN DimRegion r ON f.RegionKey = r.RegionKey
        JOIN DimDate d ON f.DateKey = d.DateKey
        WHERE d.Year = {map_year}
        GROUP BY cp.Latitude, cp.Longitude, cp.RoadName, r.RegionName
        HAVING SUM(f.AllMotorVehicles) > {min_traffic}
    """)

    if not geo.empty:
        fig = px.scatter_map(
            geo, lat="Latitude", lon="Longitude", size="TotalTraffic",
            color="TotalTraffic", hover_name="RoadName",
            hover_data=["RegionName", "TotalTraffic"],
            title=f"Traffic Hotspots ({map_year})",
            color_continuous_scale="YlOrRd",
            zoom=5, center={"lat": 53.5, "lon": -1.5},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data matching current filters.")
