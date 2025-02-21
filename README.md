# Israel Bus Locator

A Python client for tracking bus lines in Israel using the SIRI API.

## Installation

```bash
pip install israel_bus_locator
```

## Features

- Real-time bus tracking using SIRI API
- Location, speed, and bearing information
- Distance calculations from journey start and reference points
- Support for multiple bus lines and routes

## Usage

```python
from israel_bus_locator import BusTracker

tracker = BusTracker(route_mkt="123")
bus_info = await tracker.get_bus_info()
print(f"Bus location: {bus_info['location']}")
```

## Development

1. Install development dependencies:
```bash
make install-dev
```

2. Run tests:
```bash
make test
```

## License

MIT License 