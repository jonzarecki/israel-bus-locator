import pandas as pd
import datetime
from dateutil import tz
from pprint import PrettyPrinter
import sys

# Configure UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')
# Initialize PrettyPrinter with proper encoding
pp = PrettyPrinter(indent=2, width=100, sort_dicts=False)

pd.options.display.max_columns = 1000
pd.options.display.max_colwidth = 1000
pd.set_option('display.unicode.east_asian_width', True)

import stride

routes = pd.DataFrame(stride.get('/gtfs_routes/list', {'route_short_name':56,
                                              'date_from': '2025-01-18',
                                              'date_to':  '2025-01-18'}))
routes = routes[routes["agency_name"] == "מטרופולין"]

pp.pprint(routes.to_dict('records'))

exit(0)

siri_vehicle_locations_480 = pd.DataFrame(stride.iterate('/siri_vehicle_locations/list', {
    'siri_routes__line_ref': '7020',
    'siri_rides__schedualed_start_time_from': datetime.datetime(2025,1, 18, tzinfo=tz.gettz('Israel')),
    'siri_rides__schedualed_start_time_to': datetime.datetime(2025,1, 18, tzinfo=tz.gettz('Israel'))+datetime.timedelta(days=1),
    'order_by': 'recorded_at_time desc'
}, limit=1000))

print(siri_vehicle_locations_480.shape)

def localize_dates(data, dt_columns = None):
    if dt_columns is None:
        dt_columns=[]
    
    data = data.copy()
    
    for c in dt_columns:
        data[c] = pd.to_datetime(data[c]).dt.tz_convert('Israel')
    
    return data
dt_columns = ['recorded_at_time','siri_ride__scheduled_start_time']

siri_vehicle_locations_480 = localize_dates(siri_vehicle_locations_480, dt_columns)

print(siri_vehicle_locations_480.shape)

print(siri_vehicle_locations_480.head())


