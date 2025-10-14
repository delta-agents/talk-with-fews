"""
Test configuration system for supporting multiple FEWS web service URLs.

This module provides configuration for different FEWS services and their
corresponding test data, allowing tests to run against multiple services
locally while maintaining CI compatibility.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class FEWSServiceConfig:
    """Configuration for a specific FEWS web service."""

    name: str
    web_service_url: str
    db_path: str
    test_data: Dict[str, Any]


# Test data configurations for different FEWS services
FEWS_SERVICES = {
    "actueelwaterbeeld": FEWSServiceConfig(
        name="Actueel Waterbeeld",
        web_service_url="https://actueelwaterbeeld-api.hkvservices.nl/FewsWebServices",
        db_path="data/fews_config.db3",
        test_data={
            "location_filters": ["ede", "amsterdam", "rotterdam"],
            "location_ids": ["KNMIUUR278", "WS000323"],
            "parameter_ids": ["Eref.d", "WaterLevel", "Discharge"],
            "parameter_filters": ["water", "level", "speed"],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "1990-01-01T00:00:00+00:00",
            "end_time": "2025-12-31T23:59:59+00:00",
        },
    ),
    "hdsr": FEWSServiceConfig(
        name="HDSR",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHDSR",
        db_path="data/HDSR_wis.db3",
        test_data={
            "location_filters": ["gouda", "utrecht", "leiden"],
            "location_ids": ["beg_109", "beg_110"],
            "parameter_ids": ["BG.b.0", "H.G"],
            "parameter_filters": ["groundwater", "level", "height"],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
        },
    ),
    "wsvv": FEWSServiceConfig(
        name="WSVV",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesWSVV",
        db_path="data/WSDD_wis.db3",
        test_data={
            "location_filters": ["den_haag", "delft", "zoetermeer"],
            "location_ids": [
                "HL000141"
            ],  # Use only location where we know parameters exist
            "parameter_ids": [
                "Q.G",
                "T.ow.G",
            ],  # Use only parameters that exist for HL000141
            "parameter_filters": ["discharge", "temperature", "flow"],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2024-01-01T00:00:00+01:00",
            "end_time": "2024-01-14T00:00:00+01:00",
        },
    ),
    "hhd": FEWSServiceConfig(
        name="HHD",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHHD",
        db_path="data/HHD_wis.db3",
        test_data={
            "location_filters": ["hoorn", "heerhugowaard", "den_helder"],
            "location_ids": ["HHD001", "HHD002"],
            "parameter_ids": ["WaterLevel", "Discharge", "Salinity"],
            "parameter_filters": ["water", "level", "salt"],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
        },
    ),
    "scheldestromen": FEWSServiceConfig(
        name="Scheldestromen",
        web_service_url="https://data.hkvfewsscheldestromen.nl:8443/FewsWebServices",
        db_path="data/scheldestromen_wis.db3",
        test_data={
            "location_filters": ["terneuzen", "vlissingen", "antwerpen"],
            "location_ids": ["SCH001", "SCH002"],
            "parameter_ids": ["WaterLevel", "Discharge", "Tide"],
            "parameter_filters": ["water", "tide", "flow"],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
        },
    ),
}


def get_test_service_config() -> FEWSServiceConfig:
    """
    Get the FEWS service configuration based on environment variables.

    Priority:
    1. FEWS_TEST_SERVICE environment variable (for local testing)
    2. CI environment detection (defaults to actueelwaterbeeld)
    3. Default to actueelwaterbeeld

    Returns:
        FEWSServiceConfig: The selected service configuration
    """
    # Check if running in CI (GitHub Actions, etc.)
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if is_ci:
        # In CI, always use the production service
        return FEWS_SERVICES["actueelwaterbeeld"]

    # For local testing, check for explicit service selection
    test_service = os.getenv("FEWS_TEST_SERVICE", "actueelwaterbeeld")

    if test_service not in FEWS_SERVICES:
        print(
            f"Warning: Unknown FEWS_TEST_SERVICE '{test_service}', falling back to 'actueelwaterbeeld'"
        )
        test_service = "actueelwaterbeeld"

    return FEWS_SERVICES[test_service]


def get_test_data_for_service(service_name: str) -> Dict[str, Any]:
    """
    Get test data configuration for a specific service.

    Args:
        service_name: Name of the FEWS service

    Returns:
        Dict containing test data for the service
    """
    if service_name not in FEWS_SERVICES:
        raise ValueError(f"Unknown service: {service_name}")

    return FEWS_SERVICES[service_name].test_data


def get_available_services() -> list[str]:
    """Get list of available FEWS service names."""
    return list(FEWS_SERVICES.keys())


def print_service_info():
    """Print information about available services and current selection."""
    current_config = get_test_service_config()
    print(f"Current FEWS service: {current_config.name}")
    print(f"Web service URL: {current_config.web_service_url}")
    print(f"Database path: {current_config.db_path}")
    print("\nAvailable services:")
    for name, config in FEWS_SERVICES.items():
        marker = " (current)" if name == current_config.name else ""
        print(f"  - {name}: {config.name}{marker}")
    print("\nTo switch services locally, set FEWS_TEST_SERVICE environment variable:")
    print("  export FEWS_TEST_SERVICE=hdsr")
    print("  export FEWS_TEST_SERVICE=wsvv")
