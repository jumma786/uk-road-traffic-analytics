import pandas as pd 
import os 
 
files = [ 
    'data/raw/count_points.csv', 
    'data/raw/dft_traffic_counts_aadf.csv', 
    'data/raw/dft_traffic_counts_aadf_by_direction.csv', 
    'data/raw/dft_traffic_counts_raw_counts.csv', 
    'data/raw/local_authority_traffic.csv', 
    'data/raw/region_traffic_by_road_type.csv', 
    'data/raw/region_traffic_by_vehicle_type.csv' 
] 
 
for f in files: 
    if os.path.exists(f): 
        df = pd.read_csv(f, low_memory=False) 
        print(f"FILE: {os.path.basename(f)}") 
        print(f"ROWS: {len(df):,}") 
        print(f"COLUMNS: {len(df.columns)}") 
        print(f"NAMES: {list(df.columns)}") 
        print("-" * 50) 
    else: 
        print(f"MISSING: {f}") 
        print("-" * 50) 
