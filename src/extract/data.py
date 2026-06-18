import requests

url = "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow"

params = {
    "page[size]": 5
}

response = requests.get(url, params=params)

print(response.status_code)
print(response.json())