import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.transform.clean import validate_aadf, clean_aadf, VEHICLE_COLS


@pytest.fixture
def valid_df():
    return pd.DataFrame({
        "count_point_id": [1, 2, 3],
        "year": [2023, 2023, 2022],
        "region_id": [1, 2, 1],
        "local_authority_id": [10, 20, 10],
        "direction_of_travel": ["N", "S", "E"],
        "road_category": ["TM", "PA", "TA"],
        "pedal_cycles": [10, 20, 30],
        "two_wheeled_motor_vehicles": [5, 10, 15],
        "cars_and_taxis": [500, 600, 700],
        "buses_and_coaches": [20, 30, 40],
        "LGVs": [100, 200, 300],
        "HGVs_2_rigid_axle": [10, 20, 30],
        "HGVs_3_rigid_axle": [5, 10, 15],
        "HGVs_4_or_more_rigid_axle": [3, 6, 9],
        "HGVs_3_or_4_articulated_axle": [2, 4, 6],
        "HGVs_5_articulated_axle": [1, 2, 3],
        "HGVs_6_articulated_axle": [1, 1, 1],
        "all_HGVs": [22, 43, 64],
        "all_motor_vehicles": [647, 883, 1119],
    })


class TestValidateAADF:
    def test_valid_data_returns_no_issues(self, valid_df):
        issues = validate_aadf(valid_df)
        assert issues == {}

    def test_missing_columns_detected(self, valid_df):
        df = valid_df.drop(columns=["year", "region_id"])
        issues = validate_aadf(df)
        assert "missing_columns" in issues
        assert "year" in issues["missing_columns"]
        assert "region_id" in issues["missing_columns"]

    def test_negative_values_detected(self, valid_df):
        valid_df.loc[0, "cars_and_taxis"] = -100
        issues = validate_aadf(valid_df)
        assert "negative_cars_and_taxis" in issues
        assert issues["negative_cars_and_taxis"] == 1

    def test_invalid_directions_detected(self, valid_df):
        valid_df.loc[0, "direction_of_travel"] = "X"
        issues = validate_aadf(valid_df)
        assert "invalid_directions" in issues
        assert "X" in issues["invalid_directions"]

    def test_invalid_road_category_detected(self, valid_df):
        valid_df.loc[0, "road_category"] = "ZZ"
        issues = validate_aadf(valid_df)
        assert "invalid_road_categories" in issues

    def test_null_values_detected(self):
        df = pd.DataFrame({
            "count_point_id": [1, None],
            "year": [2023, 2023],
            "region_id": [1, 1],
            "local_authority_id": [10, 10],
            "direction_of_travel": ["N", "S"],
            **{col: [0, 0] for col in VEHICLE_COLS},
        })
        issues = validate_aadf(df)
        assert "null_values" in issues


class TestCleanAADF:
    def test_clean_preserves_valid_data(self, valid_df):
        result = clean_aadf(valid_df.copy())
        assert len(result) == 3

    def test_clean_removes_negative_values(self, valid_df):
        valid_df.loc[0, "cars_and_taxis"] = -100
        result = clean_aadf(valid_df.copy())
        assert (result["cars_and_taxis"] >= 0).all()

    def test_clean_filters_invalid_directions(self, valid_df):
        valid_df.loc[0, "direction_of_travel"] = "X"
        result = clean_aadf(valid_df.copy())
        assert len(result) == 2

    def test_clean_filters_out_of_range_years(self, valid_df):
        valid_df.loc[0, "year"] = 1990
        result = clean_aadf(valid_df.copy())
        assert len(result) == 2

    def test_clean_drops_null_keys(self, valid_df):
        valid_df.loc[0, "count_point_id"] = None
        result = clean_aadf(valid_df.copy())
        assert len(result) == 2

    def test_clean_coerces_non_numeric_to_zero(self, valid_df):
        valid_df.loc[0, "pedal_cycles"] = "bad"
        result = clean_aadf(valid_df.copy())
        assert result.iloc[0]["pedal_cycles"] == 0
