import pandas as pd
from sqlalchemy import create_engine
import time

conn_str = "mssql+pyodbc://localhost/UK_Road_Traffic_DW?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
engine = create_engine(conn_str)

print("Loading fact table...")

# Load mappings as dictionaries
with engine.connect() as conn:
    date_map = dict(pd.read_sql("SELECT Year, DateKey FROM DimDate", conn).values)
    region_map = dict(pd.read_sql("SELECT RegionID, RegionKey FROM DimRegion", conn).values)
    la_map = dict(pd.read_sql("SELECT LocalAuthorityID, LocalAuthorityKey FROM DimLocalAuthority", conn).values)
    cp_map = dict(pd.read_sql("SELECT CountPointID, CountPointKey FROM DimCountPoint", conn).values)

chunk_size = 10000  # Smaller chunks
total_loaded = 0

for i, chunk in enumerate(pd.read_csv('data/raw/dft_traffic_counts_aadf_by_direction.csv', 
                                         chunksize=chunk_size, 
                                         low_memory=False)):
    start_time = time.time()
    
    # Map using dictionaries
    chunk['DateKey'] = chunk['year'].map(date_map)
    chunk['RegionKey'] = chunk['region_id'].map(region_map)
    chunk['LocalAuthorityKey'] = chunk['local_authority_id'].map(la_map)
    chunk['CountPointKey'] = chunk['count_point_id'].map(cp_map)
    
    # Select columns
    fact = chunk[[
        'DateKey', 'CountPointKey', 'LocalAuthorityKey', 'RegionKey',
        'direction_of_travel', 'pedal_cycles', 'two_wheeled_motor_vehicles',
        'cars_and_taxis', 'buses_and_coaches', 'LGVs', 'HGVs_2_rigid_axle',
        'HGVs_3_rigid_axle', 'HGVs_4_or_more_rigid_axle', 'HGVs_3_or_4_articulated_axle',
        'HGVs_5_articulated_axle', 'HGVs_6_articulated_axle', 'all_HGVs', 'all_motor_vehicles'
    ]].copy()
    
    fact.columns = [
        'DateKey', 'CountPointKey', 'LocalAuthorityKey', 'RegionKey',
        'DirectionOfTravel', 'PedalCycles', 'TwoWheeledMotorVehicles',
        'CarsAndTaxis', 'BusesAndCoaches', 'LGVs', 'HGVs2RigidAxle',
        'HGVs3RigidAxle', 'HGVs4OrMoreRigidAxle', 'HGVs3Or4ArticulatedAxle',
        'HGVs5ArticulatedAxle', 'HGVs6ArticulatedAxle', 'AllHGVs', 'AllMotorVehicles'
    ]
    
    # Drop rows with missing keys
    fact = fact.dropna(subset=['DateKey', 'CountPointKey', 'LocalAuthorityKey', 'RegionKey'])
    
    # Load to SQL in smaller batches
    fact.to_sql('FactTrafficFlowDirection', engine, if_exists='append', index=False, chunksize=1000)
    
    total_loaded += len(fact)
    elapsed = time.time() - start_time
    
    print(f"Chunk {i+1}: Loaded {len(fact):,} rows | Total: {total_loaded:,} | Time: {elapsed:.1f}s")

print(f"\nFact table loaded: {total_loaded:,} rows")