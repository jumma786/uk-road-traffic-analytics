import pandas as pd 
df = pd.read_csv('data/raw/traffic_flow_by_direction.csv', low_memory=False) 
print('Rows:', len(df)) 
print('Years:', df['year'].min(), '-', df['year'].max()) 
print('2025 present:', 2025 in df.year.values) 
print('Direction counts:') 
print(df['direction_of_travel'].value_counts()) 
