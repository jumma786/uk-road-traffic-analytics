import pandas as pd 
df_dir = pd.read_csv('data/raw/traffic_flow_by_direction.csv', low_memory=False) 
df_full = pd.read_csv('data/raw/uk_traffic_full.csv', low_memory=False) 
df_100k = pd.read_csv('data/raw/uk_traffic_100k.csv', low_memory=False) 
 
# Check if uk_traffic_full is just traffic_flow_by_direction aggregated 
print("Checking if uk_traffic_full = sum of directions...") 
summed = df_dir.groupby(['count_point_id', 'year'])['all_motor_vehicles'].sum().reset_index() 
merged = summed.merge(df_full[['count_point_id', 'year', 'all_motor_vehicles']], on=['count_point_id', 'year'], suffixes=('_summed', '_full')) 
print(f"Matching rows: {(merged['all_motor_vehicles_summed'] == merged['all_motor_vehicles_full']).sum():,}") 
print(f"Total in full: {len(df_full):,}") 
 
# Check if 100k is subset of full 
print("Checking if 100k is subset of full...") 
subset_check = df_100k[['count_point_id', 'year']].merge(df_full[['count_point_id', 'year']], on=['count_point_id', 'year'], how='left', indicator=True) 
print(subset_check['_merge'].value_counts()) 
 
# Check sample overlap 
print("Sample IDs from 100k in full?") 
sample_ids = set(df_100k['count_point_id'].unique()) 
full_ids = set(df_full['count_point_id'].unique()) 
print(f"100k IDs in full: {len(sample_ids & full_ids)} / {len(sample_ids)}") 
