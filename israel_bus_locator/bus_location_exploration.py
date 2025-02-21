# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Bus Location Data API Exploration
#
# This notebook explores the bus location data using the MOT SIRI API directly.

import datetime
import sys
from pprint import PrettyPrinter

import folium
# %%
# Imports and setup
import IPython
import pandas as pd
import stride
from dateutil import tz
from IPython import get_ipython

# %%
# Configure system and pandas settings
# pass if running in jupyter notebook
try:
    # Configure UTF-8 encoding for output
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass

# Initialize PrettyPrinter with proper encoding
pp = PrettyPrinter(indent=2, width=100, sort_dicts=False)

pd.options.display.max_columns = 1000
pd.options.display.max_colwidth = 1000
pd.set_option("display.unicode.east_asian_width", True)

# %%
# Get routes data for line 56 by Metropolin

chosen_date = datetime.datetime(2025, 2, 10, tzinfo=tz.gettz("Israel"))

gtfs_routes = stride.get(
    "/gtfs_routes/list",
    {
        "route_short_name": "56",
        "agency_name": "מטרופולין",
        "date_from": chosen_date.strftime("%Y-%m-%d"),
        "date_to": chosen_date.strftime("%Y-%m-%d"),
        "limit": 1000,
    },
)

# gtfs_routes = gtfs_routes[gtfs_routes.apply(lambda x: "רדינג" in x['route_long_name'], axis=1)]

line_56_route_mkt = 23056

pd.DataFrame(gtfs_routes)


# %%
# Get SIRI rides
siri_rides = stride.get(
    "/siri_rides/list",
    {
        "scheduled_start_time_from": datetime.datetime.combine(
            chosen_date, datetime.time(), datetime.timezone.utc
        ),
        "scheduled_start_time_to": datetime.datetime.combine(
            chosen_date, datetime.time(23, 59), datetime.timezone.utc
        ),
        "siri_route__line_refs": ",".join(
            [str(gtfs_route["line_ref"]) for gtfs_route in gtfs_routes]
        ),
        "siri_route__operator_refs": ",".join(
            [str(gtfs_route["operator_ref"]) for gtfs_route in gtfs_routes]
        ),
        "order_by": "scheduled_start_time asc",
    },
    pre_requests_callback="print",
)
pd.DataFrame(siri_rides)


# %%

for siri_ride in siri_rides:
    if siri_ride["scheduled_start_time"].hour >= 7:
        break
siri_ride
# %%
# Get stops for the ride
siri_ride_stops = stride.get(
    "/siri_ride_stops/list",
    {
        "siri_ride_ids": str(siri_ride["id"]),
        "order_by": "order asc",
        "siri_ride__scheduled_start_time_from": datetime.datetime.combine(
            chosen_date, datetime.time(), datetime.timezone.utc
        ),
        "expand_related_data": True,
    },
    pre_requests_callback="print",
)
df = pd.DataFrame(siri_ride_stops)
df.loc[
    :,
    [
        "order",
        "gtfs_stop__city",
        "gtfs_stop__name",
        "gtfs_ride_stop__departure_time",
        "nearest_siri_vehicle_location__recorded_at_time",
    ],
].head()
# df.head()


# %%
# Helper function for date localization
def localize_dates(data, dt_columns=None):
    if dt_columns is None:
        dt_columns = []

    data = data.copy()

    for c in dt_columns:
        data[c] = pd.to_datetime(data[c]).dt.tz_convert("Israel")

    return data


dt_columns = ["recorded_at_time", "siri_ride__scheduled_start_time"]
siri_vehicle_locations_56 = localize_dates(siri_vehicle_locations_56, dt_columns)

print(siri_vehicle_locations_56.shape)
print(siri_vehicle_locations_56.head())

# %%
# Examine the data structure
print("Dataset shape:", siri_vehicle_locations_56.shape)
print("\nColumns in the dataset:")
for col in sorted(siri_vehicle_locations_56.columns):
    print(f"- {col}")

print("\nSample data with key information:")
display(
    siri_vehicle_locations_56[
        [
            "lon",
            "lat",
            "recorded_at_time",
            "bearing",
            "velocity",
            "distance_from_journey_start",
        ]
    ].head()
)


# %%
# Create an enhanced map visualization
def create_enhanced_bus_locations_map(locations_df):
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
        Bearing: {row['bearing']}°<br>
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


# Create and display the enhanced map
bus_map = create_enhanced_bus_locations_map(siri_vehicle_locations_56)
display(bus_map)

# %% [markdown]
# The map above shows:
# - Blue circles represent bus locations
# - Red triangles indicate the direction (bearing) of the bus
# - Click on any marker to see detailed information including:
#   - Timestamp
#   - Speed
#   - Bearing (direction)
#   - Distance from journey start
#
# The time range of the data is shown in the top-left corner.

# %%
# Search for line 56 from Reading station
# First, get all stops data to find Reading station
stops = pd.DataFrame(stride.get("/gtfs_stops"))
reading_stops = stops[stops["hebrew_name"].str.contains("רידינג", na=False)]
print("Reading station stops:")
display(reading_stops[["stop_code", "hebrew_name", "city", "lat", "lon"]])

# Get all route details for line 56 by Metropolin
route_stops = pd.DataFrame(
    stride.get(
        "/gtfs_route_stops",
        {"route_short_name": "56", "agency_name": "מטרופולין", "date": "2025-01-18"},
    )
)

# Join with stops data to get stop names
route_stops = route_stops.merge(
    stops[["stop_code", "hebrew_name", "city"]],
    left_on="stop_code",
    right_on="stop_code",
    how="left",
)

# Group by route and direction to show the first and last stops
route_details = (
    route_stops.groupby(["route_id", "direction_id"])
    .agg({"stop_sequence": ["min", "max"]})
    .reset_index()
)

# Get first and last stops for each direction
for _, route in route_details.iterrows():
    direction = "To Terminal" if route["direction_id"] == 0 else "To Origin"
    first_stop = route_stops[
        (route_stops["route_id"] == route["route_id"])
        & (route_stops["direction_id"] == route["direction_id"])
        & (route_stops["stop_sequence"] == route["stop_sequence"]["min"])
    ]
    last_stop = route_stops[
        (route_stops["route_id"] == route["route_id"])
        & (route_stops["direction_id"] == route["direction_id"])
        & (route_stops["stop_sequence"] == route["stop_sequence"]["max"])
    ]

    print(f"\nRoute 56 Direction {direction}:")
    print(
        f"First Stop: {first_stop['hebrew_name'].iloc[0]} ({first_stop['city'].iloc[0]})"
    )
    print(
        f"Last Stop: {last_stop['hebrew_name'].iloc[0]} ({last_stop['city'].iloc[0]})"
    )

    # Check if Reading station is in this route direction
    reading_in_route = route_stops[
        (route_stops["route_id"] == route["route_id"])
        & (route_stops["direction_id"] == route["direction_id"])
        & (route_stops["hebrew_name"].str.contains("רידינג", na=False))
    ]

    if not reading_in_route.empty:
        print(f"Reading station is stop #{reading_in_route['stop_sequence'].iloc[0]}")
        print(
            f"Stop details: {reading_in_route['hebrew_name'].iloc[0]} ({reading_in_route['city'].iloc[0]})"
        )

# %%


# %%
