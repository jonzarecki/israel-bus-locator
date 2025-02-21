import datetime
from unittest.mock import MagicMock, patch

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from dateutil import tz

from israel_bus_locator.bus_utils import (
    calculate_distance_to_point,
    create_enhanced_bus_locations_map,
    get_current_distances_to_ref,
    get_routes_for_route_mkt,
    get_vehicle_locations,
    localize_dates,
    plot_distances_for_rides,
    split_by_ride_id,
)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    df = pd.DataFrame(
        {
            "date_col": ["2024-02-21 10:00:00", "2024-02-21 11:00:00"],
            "other_col": [1, 2],
        }
    )
    df["date_col"] = pd.to_datetime(df["date_col"]).dt.tz_localize("UTC")
    return df


@pytest.fixture
def sample_locations_df():
    """Create a sample locations DataFrame for testing."""
    return pd.DataFrame(
        {
            "lat": [32.1, 32.2, 32.3],
            "lon": [34.8, 34.9, 35.0],
            "recorded_at_time": pd.to_datetime(
                ["2024-02-21 10:00:00", "2024-02-21 10:05:00", "2024-02-21 10:10:00"]
            ).tz_localize("Israel"),
            "velocity": [30, 35, 40],
            "siri_ride__vehicle_ref": ["V1", "V1", "V1"],
            "siri_ride_stop_id": ["S1", "S2", "S3"],
            "distance_from_journey_start": [0, 100, 200],
            "bearing": [45, 90, 135],
            "siri_ride__id": ["R1", "R1", "R2"],
        }
    )


def test_localize_dates(sample_df):
    """Test the localize_dates function."""
    result = localize_dates(sample_df, dt_columns=["date_col"])

    assert isinstance(result, pd.DataFrame)
    assert result["date_col"].dt.tz.zone == "Israel"
    assert len(result) == len(sample_df)
    assert "other_col" in result.columns


def test_localize_dates_no_columns(sample_df):
    """Test localize_dates with no columns specified."""
    result = localize_dates(sample_df)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(sample_df)
    assert result.equals(sample_df)


def test_create_enhanced_bus_locations_map(sample_locations_df):
    """Test the create_enhanced_bus_locations_map function."""
    result = create_enhanced_bus_locations_map(sample_locations_df)

    assert isinstance(result, folium.Map)
    # Check if map is centered correctly
    assert result.location == [
        sample_locations_df["lat"].mean(),
        sample_locations_df["lon"].mean(),
    ]


@patch("stride.get")
def test_get_routes_for_route_mkt(mock_stride_get):
    """Test the get_routes_for_route_mkt function."""
    mock_data = [
        {
            "route_mkt": "23056",
            "route_long_name": "רדינג Test",
            "route_direction": "1",
            "line_ref": "L1",
        },
        {
            "route_mkt": "23056",
            "route_long_name": "Other Route",
            "route_direction": "2",
            "line_ref": "L2",
        },
    ]
    mock_stride_get.return_value = mock_data

    # Test with all filters
    result = get_routes_for_route_mkt(
        "23056", "2024-02-21", "2024-02-21", filter_name="רדינג", direction="1"
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["route_long_name"] == "רדינג Test"
    assert result.iloc[0]["route_direction"] == "1"

    # Test without filters
    result = get_routes_for_route_mkt("23056", "2024-02-21", "2024-02-21")
    assert len(result) == 2


@patch("stride.iterate")
def test_get_vehicle_locations(mock_stride_iterate):
    """Test the get_vehicle_locations function."""
    mock_data = [
        {
            "recorded_at_time": "2024-02-21T10:00:00+02:00",
            "siri_ride__scheduled_start_time": "2024-02-21T09:00:00+02:00",
            "lat": 32.1,
            "lon": 34.8,
        }
    ]
    mock_stride_iterate.return_value = mock_data

    start_time = datetime.datetime(2024, 2, 21, 9, tzinfo=tz.gettz("Israel"))
    end_time = datetime.datetime(2024, 2, 21, 12, tzinfo=tz.gettz("Israel"))

    result = get_vehicle_locations("L1", start_time, end_time)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result["recorded_at_time"].dt.tz.zone == "Israel"
    assert result["siri_ride__scheduled_start_time"].dt.tz.zone == "Israel"


def test_split_by_ride_id(sample_locations_df):
    """Test the split_by_ride_id function."""
    result = split_by_ride_id(sample_locations_df)

    assert isinstance(result, list)
    assert len(result) == 2  # Two unique ride IDs in sample data
    assert all(isinstance(df, pd.DataFrame) for df in result)
    assert result[0]["siri_ride__id"].nunique() == 1


def test_calculate_distance_to_point():
    """Test the calculate_distance_to_point function."""
    ref_point = (32.0, 34.0)
    lat, lon = 32.1, 34.1

    result = calculate_distance_to_point(lat, lon, ref_point)

    assert isinstance(result, float)
    expected = np.sqrt((32.1 - 32.0) ** 2 + (34.1 - 34.0) ** 2)
    assert pytest.approx(result, rel=1e-6) == expected


def test_get_current_distances_to_ref(sample_locations_df):
    """Test the get_current_distances_to_ref function."""
    ref_point = (32.0, 34.0)

    result = get_current_distances_to_ref(sample_locations_df, ref_point)

    assert isinstance(result, dict)
    assert len(result) == 2  # Two unique ride IDs

    for ride_id, info in result.items():
        assert isinstance(info, dict)
        assert all(
            key in info
            for key in ["current_distance", "last_update", "vehicle_ref", "lat", "lon"]
        )
        assert isinstance(info["current_distance"], float)
        assert isinstance(info["last_update"], pd.Timestamp)


def test_plot_distances_for_rides(sample_locations_df):
    """Test the plot_distances_for_rides function."""
    ride_dfs = split_by_ride_id(sample_locations_df)
    ref_point = (32.0, 34.0)

    # Test that the function runs without errors
    plot_distances_for_rides(ride_dfs, ref_point)

    # Get the current figure
    fig = plt.gcf()
    ax = plt.gca()

    # Test figure properties
    assert fig.get_size_inches().tolist() == [12, 8]

    # Test that we have the correct number of lines plotted (one per ride)
    assert len(ax.lines) == len(ride_dfs)

    # Test plot labels
    assert ax.get_xlabel() == "Recorded Time"
    assert ax.get_ylabel() == "Distance from Reference Point"
    assert ax.get_title() == "Distance from Reference Point Over Time - All Rides"

    # Clear the current plot
    plt.close()
