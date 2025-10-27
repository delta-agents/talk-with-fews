"""
Error classes for FEWS flag analysis.

These classes define specific errors that can occur during flag analysis.
"""


class SeriesFlagsError(Exception):
    """Base exception for series flags analysis"""

    pass


class InvalidTimeRangeError(SeriesFlagsError):
    """Invalid time range specified"""

    def __init__(self, message: str = "Invalid time range"):
        self.message = message
        super().__init__(self.message)


class DataRetrievalError(SeriesFlagsError):
    """Error retrieving data from get_series_data"""

    def __init__(self, message: str = "Failed to retrieve timeseries data"):
        self.message = message
        super().__init__(self.message)


class UnknownFlagError(SeriesFlagsError):
    """Unknown flag value encountered"""

    def __init__(self, flag: int):
        self.message = f"Unknown flag value: {flag}"
        super().__init__(self.message)


class UnknownFlagSourceError(SeriesFlagsError):
    """Unknown flag source encountered"""

    def __init__(self, source: str):
        self.message = f"Unknown flag source: {source}"
        super().__init__(self.message)
