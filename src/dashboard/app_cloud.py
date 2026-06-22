"""
Cloud-ready Streamlit dashboard. Reads from pre-aggregated CSVs,
no SQL Server required. Deploy to Streamlit Cloud, Render, or Railway.

Usage:
    streamlit run src/dashboard/app_cloud.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="UK Road Traffic Analytics", layout="wide", page_icon="🚗")

DASH_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "dashboard"


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DASH_DATA / name)


if not DASH_DATA.exists():
    st.error("Dashboard data not found. Run `python scripts/prepare_dashboard_data.py` first.")
    st.stop()

yearly = load_csv("yearly_totals.csv")
regional = load_csv("regional_by_year.csv")
top_roads = load_csv("top_roads_by_year.csv")
geo = load_csv("geospatial_hotspots.csv")
vehicle_mix = load_csv("vehicle_mix.csv")
road_cat = load_csv("road_category_by_year.csv")

available_years = sorted(yearly["Year"].unique().tolist())

st.title("UK Road Traffic Analytics")
st.caption("1.1M+ directional traffic flow records from the UK Department for Transport")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview", "Regional", "Vehicle Mix", "Trends", "Top Roads", "Map",
])

# --- Tab 1: Overview ---
with tab1:
    st.header("Traffic Overview")

    latest = yearly.iloc[-1]
    prev = yearly.iloc[-2] if len(yearly) > 1 else latest

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Year", int(latest["Year"]))
    col2.metric(
        "Motor Vehicles",
        f"{latest['TotalMotor'] / 1e6:.1f}M",
        delta=f"{(latest['TotalMotor'] - prev['TotalMotor']) / 1e6:+.1f}M" if len(yearly) > 1 else None,
    )
    col3.metric(
        "HGVs",
        f"{latest['TotalHGV'] / 1e6:.1f}M",
        delta=f"{(latest['TotalHGV'] - prev['TotalHGV']) / 1e6:+.1f}M" if len(yearly) > 1 else None,
    )
    col4.metric("Count Points", f"{latest['CountPoints']:,.0f}")

    fig = px.bar(
        yearly, x="Year", y="TotalMotor",
        title="Total Motor Vehicle AADF by Year",
        labels={"TotalMotor": "Total AADF", "Year": "Year"},
        color_discrete_sequence=["#2196F3"],
    )
    st.plotly_chart(fig, use_container_width=True)

    yearly_pct = yearly.copy()
    yearly_pct["YoY_Growth"] = yearly_pct["TotalMotor"].pct_change() * 100
    fig2 = px.line(
        yearly_pct.dropna(subset=["YoY_Growth"]),
        x="Year", y="YoY_Growth",
        title="Year-over-Year Traffic Growth (%)",
        markers=True,
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig2, use_container_width=True)

# --- Tab 2: Regional ---
with tab2:
    st.header("Regional Analysis")
    sel_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1, key="reg_year")

    reg_filtered = regional[regional["Year"] == sel_year].sort_values("TotalMotor", ascending=True)

    fig = px.bar(
        reg_filtered, x="TotalMotor", y="RegionName", orientation="h",
        title=f"Traffic by Region ({sel_year})",
        labels={"TotalMotor": "Total AADF", "RegionName": "Region"},
        color_discrete_sequence=["#4CAF50"],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        reg_filtered[["RegionName", "TotalMotor", "TotalHGV", "CountPoints"]]
        .sort_values("TotalMotor", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
    )

# --- Tab 3: Vehicle Mix ---
with tab3:
    st.header("Vehicle Type Mix")

    col_left, col_right = st.columns(2)

    with col_left:
        totals = vehicle_mix[["Cars", "LGVs", "HGVs", "Buses", "Motorcycles", "Cycles"]].sum()
        fig = px.pie(
            values=totals.values, names=totals.index,
            title="National Vehicle Mix (Latest Year)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        fig2 = px.bar(
            vehicle_mix.melt(id_vars="RegionName", value_vars=["Cars", "LGVs", "HGVs", "Buses"]),
            x="RegionName", y="value", color="variable", barmode="group",
            title="Vehicle Types by Region",
            labels={"value": "AADF", "variable": "Type"},
        )
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    hgv_pct = vehicle_mix.copy()
    hgv_pct["HGV_Pct"] = (hgv_pct["HGVs"] / (hgv_pct["Cars"] + hgv_pct["LGVs"] + hgv_pct["HGVs"] + hgv_pct["Buses"] + hgv_pct["Motorcycles"]) * 100).round(2)
    hgv_pct = hgv_pct.sort_values("HGV_Pct", ascending=True)
    fig3 = px.bar(
        hgv_pct, x="HGV_Pct", y="RegionName", orientation="h",
        title="HGV Share by Region (%)",
        color_discrete_sequence=["#FF9800"],
    )
    st.plotly_chart(fig3, use_container_width=True)

# --- Tab 4: Trends ---
with tab4:
    st.header("Traffic Trends")

    trend = st.radio("Trend", ["COVID Impact", "Cycling", "LGV Growth", "Bus Decline", "Road Categories"], horizontal=True)

    if trend == "COVID Impact":
        covid = yearly[(yearly["Year"] >= 2017) & (yearly["Year"] <= 2023)]
        melted = covid.melt(
            id_vars="Year",
            value_vars=["TotalCars", "TotalLGVs", "TotalHGV", "TotalBuses", "TotalCycles"],
            var_name="Vehicle", value_name="AADF",
        )
        melted["Vehicle"] = melted["Vehicle"].str.replace("Total", "")
        fig = px.line(melted, x="Year", y="AADF", color="Vehicle",
                      title="COVID-19 Impact by Vehicle Type", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    elif trend == "Cycling":
        fig = px.line(yearly, x="Year", y="TotalCycles",
                      title="Pedal Cycle AADF Over Time", markers=True,
                      color_discrete_sequence=["#00BCD4"])
        st.plotly_chart(fig, use_container_width=True)

    elif trend == "LGV Growth":
        yearly_lgv = yearly.copy()
        yearly_lgv["LGV_Share"] = (yearly_lgv["TotalLGVs"] / yearly_lgv["TotalMotor"] * 100).round(2)
        fig = px.area(yearly_lgv, x="Year", y="LGV_Share",
                      title="LGV Share of Traffic (E-Commerce Indicator)",
                      color_discrete_sequence=["#9C27B0"])
        st.plotly_chart(fig, use_container_width=True)

    elif trend == "Bus Decline":
        yearly_bus = yearly.copy()
        yearly_bus["Bus_Share"] = (yearly_bus["TotalBuses"] / yearly_bus["TotalMotor"] * 100).round(3)
        fig = px.line(yearly_bus, x="Year", y="Bus_Share",
                      title="Bus & Coach Share Over Time (%)", markers=True,
                      color_discrete_sequence=["#F44336"])
        st.plotly_chart(fig, use_container_width=True)

    elif trend == "Road Categories":
        rc_year = st.selectbox("Year", available_years, index=len(available_years) - 1, key="rc_year")
        rc_filtered = road_cat[road_cat["Year"] == rc_year]
        fig = px.pie(rc_filtered, values="TotalTraffic", names="RoadCategory",
                     title=f"Traffic by Road Category ({rc_year})")
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 5: Top Roads ---
with tab5:
    st.header("Busiest Roads")
    road_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1, key="road_year")

    roads_filtered = top_roads[top_roads["Year"] == road_year].nlargest(20, "TotalTraffic")
    fig = px.bar(
        roads_filtered.sort_values("TotalTraffic"),
        x="TotalTraffic", y="RoadName", orientation="h",
        color="RoadCategory",
        title=f"Top 20 Busiest Roads ({road_year})",
        labels={"TotalTraffic": "Total AADF", "RoadName": "Road"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(roads_filtered.reset_index(drop=True), use_container_width=True)

# --- Tab 6: Map ---
with tab6:
    st.header("Traffic Hotspot Map")
    min_traffic = st.slider("Minimum Traffic", 10000, 200000, 50000, step=10000)

    geo_filtered = geo[geo["TotalTraffic"] >= min_traffic]
    st.caption(f"Showing {len(geo_filtered):,} count points")

    if not geo_filtered.empty:
        fig = px.scatter_map(
            geo_filtered, lat="Latitude", lon="Longitude",
            size="TotalTraffic", color="TotalTraffic",
            hover_name="RoadName",
            hover_data=["RegionName", "TotalTraffic"],
            title="Traffic Hotspots (Latest Year)",
            color_continuous_scale="YlOrRd",
            zoom=5, center={"lat": 53.5, "lon": -1.5},
        )
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data matching current filters.")

# --- Footer ---
st.divider()
st.caption("Data: UK Department for Transport | Built by Jumma Mohammad Teli")
