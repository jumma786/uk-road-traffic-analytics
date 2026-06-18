import pandas as pd
from sqlalchemy import create_engine

# SQL Server connection
conn_str = "mssql+pyodbc://localhost/UK_Road_Traffic_DW?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
engine = create_engine(conn_str)

# 1. Load DimDate
print("Loading DimDate...")
dates = pd.date_range('2000-01-01', '2025-12-31', freq='D')
dim_date = pd.DataFrame({
    'DateKey': dates.strftime('%Y%m%d').astype(int),
    'FullDate': dates,
    'Year': dates.year,
    'Quarter': dates.quarter,
    'Month': dates.month,
    'MonthName': dates.strftime('%B'),
    'Day': dates.day,
    'DayOfWeek': dates.dayofweek + 1,
    'DayName': dates.strftime('%A'),
    'IsWeekend': dates.dayofweek.isin([5, 6]).astype(int),
    'FiscalYear': dates.year + (dates.month >= 4).astype(int)
})
dim_date.to_sql('DimDate', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_date)} dates")

# 2. Load DimRegion
print("Loading DimRegion...")
df = pd.read_csv('data/raw/count_points.csv', usecols=['region_id', 'region_name', 'region_ons_code'])
dim_region = df[['region_id', 'region_name', 'region_ons_code']].drop_duplicates()
dim_region.columns = ['RegionID', 'RegionName', 'RegionONSCode']
dim_region.to_sql('DimRegion', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_region)} regions")

# 3. Load DimLocalAuthority
print("Loading DimLocalAuthority...")
df = pd.read_csv('data/raw/count_points.csv', usecols=['local_authority_id', 'local_authority_name', 'local_authority_code', 'region_id'])
dim_la = df[['local_authority_id', 'local_authority_name', 'local_authority_code', 'region_id']].drop_duplicates()
dim_la.columns = ['LocalAuthorityID', 'LocalAuthorityName', 'LocalAuthorityCode', 'RegionID']

# Get RegionKey mapping
with engine.connect() as conn:
    region_map = pd.read_sql("SELECT RegionKey, RegionID FROM DimRegion", conn)

# Merge to get RegionKey
dim_la = dim_la.merge(region_map, on='RegionID', how='left')
dim_la = dim_la[['LocalAuthorityID', 'RegionKey', 'LocalAuthorityName', 'LocalAuthorityCode']]
dim_la.to_sql('DimLocalAuthority', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_la)} local authorities")

# 4. Load DimCountPoint
print("Loading DimCountPoint...")
df = pd.read_csv('data/raw/count_points.csv')
dim_cp = df[['count_point_id', 'road_name', 'road_category', 'road_type', 'latitude', 'longitude', 'link_length_km']].drop_duplicates('count_point_id')
dim_cp.columns = ['CountPointID', 'RoadName', 'RoadCategory', 'RoadType', 'Latitude', 'Longitude', 'LinkLengthKm']
dim_cp.to_sql('DimCountPoint', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_cp)} count points")

print("All dimensions loaded successfully!")