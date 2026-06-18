import pandas as pd 
 
files = [ 
    'data/raw/traffic_flow_by_direction.csv', 
    'data/raw/uk_traffic_100k.csv', 
    'data/raw/uk_traffic_full.csv' 
] 
 
for f in files: 
    try: 
        df = pd.read_csv(f, low_memory=False) 
        print(f"{'='*60}") 
        print(f"FILE: {f}") 
        print(f"{'='*60}") 
        print(f"Rows: {len(df):,}") 
        print(f"Columns: {len(df.columns)}") 
        print(f"Column names: {list(df.columns)}") 
        if 'year' in df.columns: 
            print(f"Year range: {df.year.min()} - {df.year.max()}") 
        if 'count_point_id' in df.columns: 
            print(f"Unique count points: {df.count_point_id.nunique():,}") 
        print(f"Memory: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB") 
        print() 
    except Exception as e: 
        print(f"{f}: ERROR - {e}") 
        print() 
