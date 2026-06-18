import requests
import pandas as pd

all_data = []

for page in range(1, 101):

    params = {
        "page[size]": 1000,
        "page[number]": page
    }

    response = requests.get(
        "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow",
        params=params
    )

    data = response.json()["data"]

    all_data.extend(data)

    print(f"Downloaded Page {page}")

df = pd.DataFrame(all_data)

df.to_csv("uk_traffic_100k.csv", index=False)

print(df.shape)