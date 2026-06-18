import requests
import pandas as pd

BASE_URL = "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow-by-direction"

# Get metadata
response = requests.get(
    BASE_URL,
    params={"page[size]": 1000}
)

meta = response.json()

total_rows = meta["total"]
last_page = meta["last_page"]

print(f"Total Rows: {total_rows}")
print(f"Total Pages: {last_page}")

output_file = "data/raw/traffic_flow_by_direction.csv"

first_batch = True

for page in range(1, last_page + 1):

    response = requests.get(
        BASE_URL,
        params={
            "page[size]": 1000,
            "page[number]": page
        }
    )

    data = response.json()["data"]

    df = pd.DataFrame(data)

    df.to_csv(
        output_file,
        mode="a",
        header=first_batch,
        index=False
    )

    first_batch = False

    print(f"Downloaded page {page}/{last_page}")

print("Download Complete")