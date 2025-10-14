"""
Test data helpers for dynamic test configuration.

This module provides helper functions to get test data that's appropriate
for the currently selected FEWS service.
"""

from tests.test_config import get_test_service_config


def get_test_location_filter() -> str:
    """
    Get a location filter string appropriate for the current FEWS service.

    Returns:
        str: A location filter that should return results for the current service
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Return the first location filter from the service's test data
    return test_data["location_filters"][0]


def get_test_location_id() -> str:
    """
    Get a location ID appropriate for the current FEWS service.

    Returns:
        str: A location ID that should exist in the current service
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Return the first location ID from the service's test data
    return test_data["location_ids"][0]


def get_test_parameter_id() -> str:
    """
    Get a parameter ID appropriate for the current FEWS service.

    Returns:
        str: A parameter ID that should exist in the current service
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Return the first parameter ID from the service's test data
    return test_data["parameter_ids"][0]


def get_expected_location_count() -> int:
    """
    Get the expected number of locations for the current FEWS service.

    Returns:
        int: Expected number of locations
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    return test_data["expected_location_count"]


def get_expected_parameter_count() -> int:
    """
    Get the expected number of parameters for the current FEWS service.

    Returns:
        int: Expected number of parameters
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    return test_data["expected_parameter_count"]


def get_test_assertion_data() -> dict:
    """
    Get assertion data appropriate for the current FEWS service.

    Returns:
        dict: Dictionary containing assertion data for the current service
    """
    service_config = get_test_service_config()
    test_data = service_config.test_data

    return {
        "location_filter": test_data["location_filters"][0],
        "location_id": test_data["location_ids"][0],
        "parameter_id": test_data["parameter_ids"][0],
        "expected_location_count": test_data["expected_location_count"],
        "expected_parameter_count": test_data["expected_parameter_count"],
        "service_name": service_config.name,
    }


def get_all_test_data() -> dict:
    """
    Get all test data for the current FEWS service.

    Returns:
        dict: All test data for the current service
    """
    service_config = get_test_service_config()
    return service_config.test_data
