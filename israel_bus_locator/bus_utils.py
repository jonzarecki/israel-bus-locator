import datetime
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import stride
from dateutil import tz
import folium
from matplotlib import pyplot as plt


def localize_dates(
    data: pd.DataFrame, dt_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    if dt_columns is None:
        dt_columns = []
    if not isinstance(data, pd.DataFrame):
        raise ValueError("data must be a pandas DataFrame")
    if data.empty:
        return data
    data = data.copy()

    for c in dt_columns:
        data[c] = pd.to_datetime(data[c]).dt.tz_convert("Israel")

    return data


def create_enhanced_bus_locations_map(locations_df):
    """Create an enhanced map visualization"""

    # Calculate the center of the map (mean of coordinates)
    center_lat = locations_df["lat"].mean()
    center_lon = locations_df["lon"].mean()

    # Create a map centered on the mean position
    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=13, tiles="cartodbpositron"
    )  # Using a cleaner map style

    # Add a timestamp to show data freshness
    latest_time = locations_df["recorded_at_time"].max()
    earliest_time = locations_df["recorded_at_time"].min()

    title_html = f"""
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 300px; height: 60px; 
                    z-index:9999; font-size:14px; background-color: white;
                    padding: 10px; border-radius: 5px;">
            <b>Bus Locations Data</b><br>
            Time Range: {earliest_time.strftime('%H:%M:%S')} - {latest_time.strftime('%H:%M:%S')}
        </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # Create a feature group for bus markers
    bus_locations = folium.FeatureGroup(name="Bus Locations")

    # Add markers for each bus location with enhanced information
    for idx, row in locations_df.iterrows():
        # Create detailed popup text
        popup_text = f"""
        <b>Bus Details:</b><br>
        Time: {row['recorded_at_time'].strftime('%H:%M:%S')}<br>
        Speed: {row['velocity']:.1f} km/h<br>
        siri_ride__vehicle_ref: {row['siri_ride__vehicle_ref']}<br>
        siri_ride_stop_id: {row['siri_ride_stop_id']}<br>
        siri_ride_stop_id
        Distance from start: {row['distance_from_journey_start']:.1f}m
        """

        # Create a circle marker with rotation based on bearing
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            popup=folium.Popup(popup_text, max_width=200),
            tooltip=f"Click for details",
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.7,
            weight=2,
        ).add_to(bus_locations)

        # Add a small line indicating direction (bearing)
        if pd.notna(row["bearing"]):
            folium.RegularPolygonMarker(
                location=[row["lat"], row["lon"]],
                number_of_sides=3,
                radius=4,
                rotation=row["bearing"],
                color="red",
                fill=True,
                fill_color="red",
            ).add_to(bus_locations)

    bus_locations.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def get_routes_for_route_mkt(
    route_mkt: str,
    date_from: str,
    date_to: str,
    filter_name: Optional[str] = None,
    direction: Optional[str] = None,
) -> pd.DataFrame:
    """Get routes dataframe filtered by route_mkt and optionally by name and direction.

    Args:
        route_mkt (str): Route market ID
        date_from (str): Start date in YYYY-MM-DD format
        date_to (str): End date in YYYY-MM-DD format
        filter_name (str, optional): String to filter route names. Defaults to None.
        direction (str, optional): Direction to filter by. Defaults to None.

    Returns:
        pd.DataFrame: Filtered routes dataframe
    """
    routes_df = pd.DataFrame(
        stride.get(
            "/gtfs_routes/list",
            {"route_mkt": route_mkt, "date_from": date_from, "date_to": date_to},
        )
    )
    if routes_df.empty:
        return routes_df

    if filter_name:
        routes_df = routes_df[
            routes_df["route_long_name"].apply(lambda s: filter_name in s)
        ]

    if direction:
        routes_df = routes_df[routes_df["route_direction"] == direction]

    return routes_df


def get_vehicle_locations(
    line_ref: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int = 100_000,
) -> pd.DataFrame:
    """Get vehicle locations for a specific line reference and time range.

    Args:
        line_ref (str): Line reference ID
        start_time (datetime): Start time with timezone
        end_time (datetime): End time with timezone
        limit (int, optional): Maximum number of records to retrieve. Defaults to 100_000.

    Returns:
        pd.DataFrame: Vehicle locations dataframe with localized dates
    """
    locations_df = pd.DataFrame(
        stride.iterate(
            "/siri_vehicle_locations/list",
            {
                "siri_routes__line_ref": line_ref,
                "siri_rides__schedualed_start_time_from": start_time,
                "siri_rides__schedualed_start_time_to": end_time,
                "order_by": "recorded_at_time desc",
                "limit": -1,
            },
            limit=limit,
        )
    )  #  pre_requests_callback='print'

    dt_columns = ["recorded_at_time", "siri_ride__scheduled_start_time"]
    return localize_dates(locations_df, dt_columns)


def split_by_ride_id(locations_df: pd.DataFrame) -> List[pd.DataFrame]:
    """Split the locations dataframe into separate dataframes by ride_id.

    Args:
        locations_df (pd.DataFrame): DataFrame containing vehicle locations

    Returns:
        List[pd.DataFrame]: List of DataFrames, one for each unique ride_id
    """
    ride_ids = locations_df["siri_ride__id"].unique()
    return [
        locations_df[locations_df["siri_ride__id"] == ride_id].copy()
        for ride_id in ride_ids
    ]


def plot_distances_for_rides(
    ride_dfs: List[pd.DataFrame],
    ref_point: Tuple[float, float] = (32.090260, 34.782621),
):
    """Plot distances from reference point over time for multiple rides.

    Args:
        ride_dfs (List[pd.DataFrame]): List of DataFrames containing ride data
        ref_point (Tuple[float, float], optional): Reference point (lat, lon).
            Defaults to (32.090260, 34.782621).
    """

    plt.figure(figsize=(12, 8))

    for i, df in enumerate(ride_dfs):
        # Sort by recorded time
        sorted_locations = df.sort_values("recorded_at_time")

        # Calculate distance from reference point
        sorted_locations["distance_from_ref"] = (
            (sorted_locations["lat"] - ref_point[0]) ** 2
            + (sorted_locations["lon"] - ref_point[1]) ** 2
        ) ** 0.5

        # Plot with a different color and label for each ride
        plt.plot(
            sorted_locations["recorded_at_time"],
            sorted_locations["distance_from_ref"],
            marker="o",
            label=f'Ride {sorted_locations["siri_ride__id"].iloc[0]}',
            alpha=0.7,
        )

    plt.title("Distance from Reference Point Over Time - All Rides")
    plt.xlabel("Recorded Time")
    plt.ylabel("Distance from Reference Point")
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()


def calculate_distance_to_point(
    lat: float, lon: float, ref_point: Tuple[float, float]
) -> float:
    """Calculate the Euclidean distance between a point and reference point.

    Args:
        lat (float): Latitude of the point
        lon (float): Longitude of the point
        ref_point (Tuple[float, float]): Reference point (lat, lon)

    Returns:
        float: Euclidean distance between the points
    """
    return ((lat - ref_point[0]) ** 2 + (lon - ref_point[1]) ** 2) ** 0.5


def get_current_distances_to_ref(
    locations_df: pd.DataFrame, ref_point: Tuple[float, float] = (32.090260, 34.782621)
) -> Dict[str, Dict]:
    """Get the current (latest) distance to reference point for all rides.

    Args:
        locations_df (pd.DataFrame): DataFrame containing vehicle locations
        ref_point (Tuple[float, float], optional): Reference point (lat, lon).
            Defaults to (32.090260, 34.782621).

    Returns:
        Dict[str, Dict]: Dictionary with ride_ids as keys and dictionaries containing:
            - current_distance: distance to reference point
            - last_update: timestamp of the last update
            - vehicle_ref: vehicle reference ID
            - lat: last known latitude
            - lon: last known longitude
    """
    ride_dfs = split_by_ride_id(locations_df)
    current_distances = {}

    for df in ride_dfs:
        # Get the latest record for this ride
        latest = df.sort_values("recorded_at_time").iloc[-1]

        ride_id = str(latest["siri_ride__id"])
        current_distances[ride_id] = {
            "current_distance": calculate_distance_to_point(
                latest["lat"], latest["lon"], ref_point
            ),
            "last_update": latest["recorded_at_time"],
            "vehicle_ref": latest["siri_ride__vehicle_ref"],
            "lat": latest["lat"],
            "lon": latest["lon"],
        }

    return current_distances


if __name__ == "__main__":
    # Example usage with current values
    date_from = "2025-02-19"
    date_to = "2025-02-19"

    # Get routes for Reading direction 1
    routes_df = get_routes_for_route_mkt(
        "23056", date_from, date_to, filter_name="רדינג", direction="1"
    )

    line_ref = routes_df["line_ref"].iloc[0]

    # Get vehicle locations for the specified time range
    start_time = datetime.datetime(2025, 2, 19, 9, tzinfo=tz.gettz("Israel"))
    end_time = datetime.datetime(2025, 2, 19, 12, tzinfo=tz.gettz("Israel"))

    siri_vehicle_locations_480 = get_vehicle_locations(line_ref, start_time, end_time)

    # Get current distances for all rides
    current_distances = get_current_distances_to_ref(siri_vehicle_locations_480)
    print("\nCurrent distances to reference point for all rides:")
    for ride_id, info in current_distances.items():
        print(f"\nRide {ride_id}:")
        print(f"  Distance: {info['current_distance']:.4f}")
        print(f"  Last Update: {info['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Vehicle: {info['vehicle_ref']}")
        print(f"  Location: ({info['lat']:.6f}, {info['lon']:.6f})")

    # Split into separate rides and plot
    ride_dfs = split_by_ride_id(siri_vehicle_locations_480)
    plot_distances_for_rides(ride_dfs)
    plt.show()

    # Previous analysis for single ride
    # Filter for the newest siri_ride__id
    newest_ride_id = siri_vehicle_locations_480["siri_ride__id"].iloc[
        0
    ]  # sorted by desc
    siri_vehicle_locations_480 = siri_vehicle_locations_480[
        siri_vehicle_locations_480["siri_ride__id"] == newest_ride_id
    ]

    print(siri_vehicle_locations_480.shape)
    # siri_vehicle_locations_480 = siri_vehicle_locations_480.iloc[:10]

    # Calculate distances from reference point
    ref_point = (32.090260, 34.782621)
    # Calculate distance from reference point for each location
    siri_vehicle_locations_480["distance_from_ref"] = (
        (siri_vehicle_locations_480["lat"] - ref_point[0]) ** 2
        + (siri_vehicle_locations_480["lon"] - ref_point[1]) ** 2
    ) ** 0.5

    # Sort by recorded time to analyze sequence
    sorted_locations = siri_vehicle_locations_480.sort_values("recorded_at_time")

    # Calculate distance from reference point for each location
    sorted_locations["distance_from_ref"] = (
        (sorted_locations["lat"] - ref_point[0]) ** 2
        + (sorted_locations["lon"] - ref_point[1]) ** 2
    ) ** 0.5

    # Plot the distances over time
    plt.figure(figsize=(10, 6))
    plt.plot(
        sorted_locations["recorded_at_time"],
        sorted_locations["distance_from_ref"],
        marker="o",
    )
    # plt.plot(sorted_locations['recorded_at_time'], sorted_locations['distance_from_journey_start'], marker='o')
    plt.title("Distance from Reference Point Over Time")
    plt.xlabel("Recorded Time")
    plt.ylabel("Distance from Reference Point")
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    plt.show()
