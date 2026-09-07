from app.integrations.satellite import SatelliteAdapterProtocol, FixtureSatelliteAdapter
from app.integrations.opendrift import DriftAdapterProtocol, OpenDriftAdapter
from app.integrations.global_fishing_watch import AISAdapterProtocol, FixtureAISAdapter
from app.integrations.weather import WeatherAdapterProtocol, FixtureWeatherAdapter

__all__ = [
    "SatelliteAdapterProtocol", "FixtureSatelliteAdapter",
    "DriftAdapterProtocol", "OpenDriftAdapter",
    "AISAdapterProtocol", "FixtureAISAdapter",
    "WeatherAdapterProtocol", "FixtureWeatherAdapter"
]
