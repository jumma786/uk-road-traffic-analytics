# UK Road Traffic Analytics

> A full-stack data warehouse and analytics platform for UK Department for Transport (DfT) road traffic data.
> Built on a SQL Server star schema with an ETL pipeline that loads **1.1M+ directional traffic flow records**, a Streamlit dashboard, REST API, and automated CI/CD.

[![CI](https://github.com/jumma786/uk-road-traffic-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/jumma786/uk-road-traffic-analytics/actions/workflows/ci.yml)

---

## Live Dashboard

**Streamlit Dashboard**: Run locally with `streamlit run src/dashboard/app.py` — opens at [http://localhost:8501](http://localhost:8501)

**REST API**: Run with `uvicorn src.api.app:app --reload` — Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs)

### Dashboard Features

| Tab | Description |
|-----|-------------|
| **Overview** | KPI metrics + yearly traffic bar chart |
| **Regional** | Horizontal bar chart by region with year selector |
| **Vehicle Mix** | Pie chart + grouped bar chart by vehicle type |
| **Trends** | COVID impact, cycling, LGV growth, bus decline |
| **Map** | Interactive scatter map of traffic hotspots with filters |

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/tables` | Row counts for all warehouse tables |
| `GET /api/regions` | List of UK regions |
| `GET /api/traffic/yearly` | Yearly traffic totals |
| `GET /api/traffic/by-region?year=2023` | Traffic breakdown by region |
| `GET /api/traffic/top-roads?year=2023&limit=10` | Busiest roads |
| `GET /api/traffic/vehicle-mix?year=2023` | Vehicle type breakdown |
| `GET /api/traffic/geospatial?year=2023` | Lat/long hotspot data |

---

## Architecture

```
DfT API ──► src/extract/ ──► data/raw/*.csv
                                  │
                          src/transform/ (validation + cleaning)
                                  │
                          src/load/ ──► SQL Server (UK_Road_Traffic_DW)
                                            │
                                            ├── DimDate
                                            ├── DimRegion
                                            ├── DimLocalAuthority
                                            ├── DimCountPoint
                                            └── FactTrafficFlowDirection
                                                 │
                              ┌──────────────────┼──────────────────┐
                              │                  │                  │
                    sql/business_queries    src/api/app.py    src/dashboard/app.py
                              │                  │                  │
                    reports/*.csv         REST API (:8000)   Streamlit (:8501)
```

---

## Data Sources

| File | Records | Description |
| :--- | :------ | :---------- |
| `dft_traffic_counts_aadf_by_direction.csv` | 1,135,556 | AADF counts by direction (primary fact source) |
| `count_points.csv` | 46,754 | Traffic sensor locations with coordinates |
| `dft_traffic_counts_raw_counts.csv` | 5.3M+ | Raw hourly counts per count point |
| `MRDB_2025_published.shp` | -- | Major Road Database shapefile for geospatial mapping |

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
git clone https://github.com/jumma786/uk-road-traffic-analytics.git
cd uk-road-traffic-analytics
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

### 5. Launch Dashboard

```bash
streamlit run src/dashboard/app.py
```

### 6. Launch REST API

```bash
uvicorn src.api.app:app --reload
```

### 7. Run Tests

```bash
pytest tests/ -v
```

### 8. Docker

```bash
docker compose up        # starts API (port 8000) + dashboard (port 8501)
```

---

## Business Queries

### Core Queries (sql/business_queries.sql)

| # | Query | Description |
| :-: | :---- | :---------- |
| 1 | **Regional Traffic Summary** | Total vehicles by region for 2023 |
| 2 | **Top 10 Busiest Roads** | Highest-traffic roads since 2020 |
| 3 | **Year-over-Year Growth** | Annual traffic growth trend with LAG window function |
| 4 | **HGV vs Passenger Mix** | Heavy goods vs passenger vehicle ratio by region |
| 5 | **Local Authority Growth** | 5-year growth comparison (2018 vs 2023) |
| 6 | **Geospatial Hotspots** | Lat/long with traffic volumes for map visualization |

### Advanced Queries (sql/advanced_queries.sql)

COVID-19 impact analysis, cycling modal shift, directional imbalance (commuter corridors), vehicle-kilometres by region, road category trends, HGV axle breakdown, LGV e-commerce growth, congestion proxy, motorway vs A-road, bus/coach decline, motorcycle trends, and count point coverage analysis.

---

## Project Structure

```
uk-road-traffic-analytics/
│
├── .github/workflows/ci.yml    # GitHub Actions CI (ruff + pytest)
├── Dockerfile                   # Container image
├── docker-compose.yml           # API + Dashboard services
├── .env.example                 # Environment config template
├── requirements.txt             # Python dependencies
│
├── config/
│   └── settings.py              # Centralized settings with dotenv
│
├── data/
│   ├── metadata/                # Traffic data documentation (PDF)
│   ├── raw/                     # Source CSVs and shapefiles
│   ├── processed/               # Derived datasets (GeoJSON, aggregated CSV)
│   └── staging/                 # ETL intermediate files
│
├── notebooks/
│   ├── exploration.ipynb        # Data exploration and shapefile processing
│   └── Untitled.ipynb           # API discovery and endpoint testing
│
├── powerbi/                     # Power BI setup guide + DAX measures
├── reports/                     # Exported CSVs and generated charts
│
├── scripts/
│   ├── run_etl.py               # ETL orchestrator (full/incremental)
│   ├── data_quality.py          # Automated quality checks (6 checks)
│   ├── visualize.py             # Chart generator (7 matplotlib charts)
│   ├── export_reports.py        # Business query CSV exporter (14 queries)
│   ├── analyze_aadf.py          # AADF analysis (7 reports)
│   ├── analyze_raw_counts.py    # Hourly/seasonal pattern analysis
│   └── check_*.py               # Data validation scripts
│
├── sql/
│   ├── create_database.sql      # Database creation
│   ├── create_tables.sql        # Star schema DDL (5 tables)
│   ├── indexes.sql              # 10 performance indexes
│   ├── business_queries.sql     # 6 core analytical queries
│   └── advanced_queries.sql     # 16 advanced analytical queries
│
├── src/
│   ├── api/app.py               # FastAPI REST API (7 endpoints)
│   ├── dashboard/app.py         # Streamlit dashboard (5 tabs)
│   ├── extract/                 # DfT API data downloaders
│   ├── load/                    # SQL Server loaders (full + incremental)
│   ├── transform/clean.py       # Data validation and cleaning
│   └── utils/db.py              # Database connection helpers
│
└── tests/                       # Unit tests (24 tests, pytest)
    ├── test_clean.py            # Transform validation tests
    ├── test_settings.py         # Config tests
    ├── test_extract.py          # API extraction tests (mocked)
    └── test_db.py               # Database connection tests (mocked)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Database** | SQL Server (star schema) |
| **ETL** | Python, pandas, SQLAlchemy, pyodbc |
| **API** | FastAPI, Uvicorn |
| **Dashboard** | Streamlit, Plotly |
| **Visualization** | Matplotlib, Plotly |
| **Geospatial** | GeoPandas, GeoJSON, Shapefiles |
| **Testing** | pytest, responses (HTTP mocking) |
| **CI/CD** | GitHub Actions (ruff lint + pytest) |
| **Containerization** | Docker, Docker Compose |

---

## Author

**Jumma Mohammad Teli**

- GitHub: [@jumma786](https://github.com/jumma786)
- Email: jummamohammad477@gmail.com

---

## License

This project uses open data from the [UK Department for Transport](https://roadtraffic.dft.gov.uk). Data is published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
