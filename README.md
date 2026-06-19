# UK Road Traffic Analytics

A data warehouse and analytics platform for UK Department for Transport (DfT) road traffic data. Built on a SQL Server star schema with an ETL pipeline that loads 1.1M+ directional traffic flow records from the DfT Road Traffic Statistics API and published CSV datasets.

## Architecture

```
data/raw/*.csv ──► scripts/etl_pipeline.py ──► SQL Server (UK_Road_Traffic_DW)
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

## Data Sources

| File | Records | Description |
|------|---------|-------------|
| `dft_traffic_counts_aadf_by_direction.csv` | 1,135,556 | AADF counts by direction (primary fact source) |
| `count_points.csv` | 46,754 | Traffic sensor locations with coordinates |
| `dft_traffic_counts_raw_counts.csv` | — | Raw hourly counts per count point |
| `MRDB_2025_published.shp` | — | Major Road Database shapefile for geospatial mapping |
| `local_authority_traffic.csv` | — | Aggregated traffic by local authority |
| `region_traffic_by_road_type.csv` | — | Regional traffic split by road category |
| `region_traffic_by_vehicle_type.csv` | — | Regional traffic split by vehicle type |

Data sourced from [DfT Road Traffic Statistics](https://roadtraffic.dft.gov.uk) and the [DfT AADF API](https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow).

## Star Schema

- **DimDate** — Calendar attributes (year, quarter, month, day, fiscal year, weekend flag)
- **DimRegion** — UK geographic regions with ONS codes
- **DimLocalAuthority** — Local authorities linked to regions
- **DimCountPoint** — Traffic sensor metadata (road name, category, lat/long, link length)
- **FactTrafficFlowDirection** — Directional AADF counts with 12 vehicle-type measures

## Setup

### Prerequisites

- Python 3.10+
- SQL Server (local or remote)
- ODBC Driver 17+ for SQL Server

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Create the Database

Run the SQL scripts in order against your SQL Server instance:

```sql
-- 1. Create database
sqlcmd -i sql/create_database.sql

-- 2. Create tables (star schema)
sqlcmd -i sql/create_tables.sql

-- 3. Create indexes
sqlcmd -i sql/indexes.sql
```

### Run the ETL Pipeline

```bash
python scripts/etl_pipeline.py --server YOUR_SERVER --database UK_Road_Traffic_DW
```

This loads dimensions first (DimDate, DimRegion, DimLocalAuthority, DimCountPoint), then the fact table with foreign key lookups.

### Export Reports

```bash
python scripts/export_reports.py --server YOUR_SERVER --database UK_Road_Traffic_DW
```

Exports all 6 business queries as CSV files to `reports/`.

## Business Queries

| Query | Description |
|-------|-------------|
| Regional Traffic Summary | Total vehicles by region for 2023 |
| Top 10 Busiest Roads | Highest-traffic roads since 2020 |
| Year-over-Year Growth | Annual traffic growth trend with LAG window function |
| HGV vs Passenger Mix | Heavy goods vs passenger vehicle ratio by region |
| Local Authority Growth | 5-year growth comparison (2018 vs 2023) |
| Geospatial Hotspots | Lat/long with traffic volumes for map visualization |

## Project Structure

```
├── data/
│   ├── raw/                  # Source CSV and shapefile data
│   ├── processed/            # Derived datasets (GeoJSON, aggregated CSV)
│   ├── staging/              # ETL intermediate files
│   └── sql_exports/          # Query result exports
├── notebooks/                # Exploratory analysis (API discovery)
├── powerbi/                  # Power BI dashboard files
├── reports/                  # Exported business query results
├── scripts/
│   ├── etl_pipeline.py       # Main ETL pipeline
│   └── export_reports.py     # Business query export script
└── sql/
    ├── create_database.sql   # Database creation
    ├── create_tables.sql     # Star schema DDL
    ├── indexes.sql           # Performance indexes
    └── business_queries.sql  # Analytical queries
```
