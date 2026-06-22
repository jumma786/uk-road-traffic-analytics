# UK Road Traffic Analytics

> A data warehouse and analytics platform for UK Department for Transport (DfT) road traffic data.
> Built on a SQL Server star schema with an ETL pipeline that loads **1.1M+ directional traffic flow records** from the DfT Road Traffic Statistics API and published CSV datasets.

---

## Architecture

```
DfT API ──► src/extract/ ──► data/raw/*.csv
                                  │
                          src/transform/ (cleaning)
                                  │
                          src/load/ ──► SQL Server (UK_Road_Traffic_DW)
                                            │
                                            ├── DimDate
                                            ├── DimRegion
                                            ├── DimLocalAuthority
                                            ├── DimCountPoint
                                            └── FactTrafficFlowDirection
                                                 │
                                    sql/business_queries.sql
                                                 │
                                 scripts/export_reports.py ──► reports/*.csv
                                                 │
                                            Power BI Dashboard
```

---

## Data Sources

| File | Records | Description |
| :--- | :------ | :---------- |
| `dft_traffic_counts_aadf_by_direction.csv` | 1,135,556 | AADF counts by direction (primary fact source) |
| `count_points.csv` | 46,754 | Traffic sensor locations with coordinates |
| `dft_traffic_counts_raw_counts.csv` | -- | Raw hourly counts per count point |
| `MRDB_2025_published.shp` | -- | Major Road Database shapefile for geospatial mapping |
| `local_authority_traffic.csv` | -- | Aggregated traffic by local authority |
| `region_traffic_by_road_type.csv` | -- | Regional traffic split by road category |
| `region_traffic_by_vehicle_type.csv` | -- | Regional traffic split by vehicle type |

Data sourced from [DfT Road Traffic Statistics](https://roadtraffic.dft.gov.uk) and the [DfT AADF API](https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow).

---

## Star Schema

| Table | Type | Description |
| :---- | :--- | :---------- |
| **DimDate** | Dimension | Calendar attributes (year, quarter, month, day, fiscal year, weekend flag) |
| **DimRegion** | Dimension | UK geographic regions with ONS codes |
| **DimLocalAuthority** | Dimension | Local authorities linked to regions |
| **DimCountPoint** | Dimension | Traffic sensor metadata (road name, category, lat/long, link length) |
| **FactTrafficFlowDirection** | Fact | Directional AADF counts with 12 vehicle-type measures |

---

## Setup

### Prerequisites

- Python 3.10+
- SQL Server (local or remote)
- ODBC Driver 17+ for SQL Server

### 1. Install Dependencies

```bash
pip install -r requirements.txt
cp .env.example .env   # edit with your SQL Server details
```

### 2. Create the Database

```bash
sqlcmd -i sql/create_database.sql
sqlcmd -i sql/create_tables.sql
sqlcmd -i sql/indexes.sql
```

### 3. Run the Full ETL Pipeline

```bash
python scripts/run_etl.py                 # full pipeline
python scripts/run_etl.py --incremental   # only load new years
python scripts/run_etl.py --skip-extract  # reload existing data only
```

Or run steps individually:

```bash
python src/extract/download_traffic_flow_by_direction.py
python src/load/load_dimensions.py
python src/load/load_fact_table.py
python scripts/export_reports.py
python scripts/visualize.py
```

### 4. Data Quality Checks

```bash
python scripts/data_quality.py
```

### 5. Launch Dashboard (no Power BI required)

```bash
streamlit run src/dashboard/app.py
```

### 6. Launch REST API

```bash
uvicorn src.api.app:app --reload
# API docs at http://localhost:8000/docs
```

### 7. Docker

```bash
docker compose up        # starts API + dashboard
```

---

## Business Queries

| # | Query | Description |
| :-: | :---- | :---------- |
| 1 | **Regional Traffic Summary** | Total vehicles by region for 2023 |
| 2 | **Top 10 Busiest Roads** | Highest-traffic roads since 2020 |
| 3 | **Year-over-Year Growth** | Annual traffic growth trend with LAG window function |
| 4 | **HGV vs Passenger Mix** | Heavy goods vs passenger vehicle ratio by region |
| 5 | **Local Authority Growth** | 5-year growth comparison (2018 vs 2023) |
| 6 | **Geospatial Hotspots** | Lat/long with traffic volumes for map visualization |

---

## Project Structure

```
uk-road-traffic-analytics/
│
├── data/
│   ├── metadata/             # Traffic data documentation (PDF)
│   ├── raw/                  # Source CSVs and shapefiles
│   ├── processed/            # Derived datasets (GeoJSON, aggregated CSV)
│   ├── sql_exports/          # Query result exports
│   └── staging/              # ETL intermediate files
│
├── notebooks/
│   ├── exploration.ipynb     # Data exploration and shapefile processing
│   └── Untitled.ipynb        # API discovery and endpoint testing
│
├── powerbi/                  # Power BI dashboard setup guide
├── reports/                  # Exported business query results
│
├── scripts/
│   ├── export_reports.py     # Business query CSV exporter
│   ├── check_all.py          # Data file inventory check
│   ├── check_all_files.py    # Extended file format check
│   ├── check_data.py         # Direction data validation
│   └── check_relationship.py # Dataset relationship verification
│
├── sql/
│   ├── create_database.sql   # Database creation
│   ├── create_tables.sql     # Star schema DDL
│   ├── indexes.sql           # Performance indexes
│   └── business_queries.sql  # Analytical queries
│
├── tests/                    # Unit tests (pytest)
│
└── src/
    ├── api/                  # FastAPI REST endpoints
    │   └── app.py
    ├── dashboard/            # Streamlit web dashboard
    │   └── app.py
    ├── extract/              # DfT API data downloaders
    │   ├── data.py           # API endpoint testing
    │   ├── download_data.py  # Bulk AADF download (100K sample)
    │   └── download_traffic_flow_by_direction.py
    ├── load/                 # SQL Server loaders
    │   ├── load_dimensions.py   # Dimension table ETL
    │   ├── load_fact_table.py   # Fact table ETL with chunked inserts
    │   └── load_incremental.py  # Incremental year-based loading
    ├── transform/            # Data cleaning and transformation
    └── utils/                # Shared utilities
```
