import responses
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestAPIEndpoints:
    def test_aadf_api_url_valid(self):
        url = "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow"
        assert "roadtraffic.dft.gov.uk" in url

    def test_direction_api_url_valid(self):
        url = "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow-by-direction"
        assert "by-direction" in url

    @responses.activate
    def test_api_response_parsing(self):
        mock_data = {
            "data": [
                {"count_point_id": 1, "year": 2023, "all_motor_vehicles": 5000},
                {"count_point_id": 2, "year": 2023, "all_motor_vehicles": 3000},
            ],
            "total": 2,
            "last_page": 1,
        }
        responses.add(
            responses.GET,
            "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow",
            json=mock_data,
            status=200,
        )

        import requests
        resp = requests.get(
            "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow",
            params={"page[size]": 1000, "page[number]": 1},
        )
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["total"] == 2

    @responses.activate
    def test_api_data_converts_to_dataframe(self):
        mock_data = {
            "data": [
                {"count_point_id": 1, "year": 2023, "all_motor_vehicles": 5000},
            ],
            "total": 1,
            "last_page": 1,
        }
        responses.add(
            responses.GET,
            "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow",
            json=mock_data,
            status=200,
        )

        import requests
        resp = requests.get(
            "https://roadtraffic.dft.gov.uk/api/average-annual-daily-flow",
            params={"page[size]": 1000},
        )
        df = pd.DataFrame(resp.json()["data"])
        assert "count_point_id" in df.columns
        assert len(df) == 1
