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
            "parameter_ids": ["Eref.d", "Q.G", "H.B"],
            "parameter_filters": ["water", "level", "Q.G"],
            "validated_combinations": [
                {
                    "location_id": "KNMIUUR278",
                    "parameter_id": "Eref.d",
                    "module_instance_id": "im.wiwb.knmi",
                },
                {
                    "location_id": "KNMIUUR278",
                    "parameter_id": "Q.G",
                    "module_instance_id": "im.wiwb.knmi",
                },
                {
                    "location_id": "KNMIUUR278",
                    "parameter_id": "H.B",
                    "module_instance_id": "im.wiwb.knmi",
                },
            ],
            # Test cases for multiple locations/parameters
            "multiple_location_test": {
                "parameter_id": "Eref.d",
                "location_id": ["KNMIUUR278", "WS000323"],
                "description": "Single parameter with multiple locations",
            },
            "multiple_parameter_test": {
                "parameter_id": ["Eref.d", "Q.G", "H.B"],
                "location_id": "KNMIUUR278",
                "description": "Multiple parameters with single location",
            },
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "1990-01-01T00:00:00+00:00",
            "end_time": "2025-12-31T23:59:59+00:00",
            # Module instance mapping for test combinations
            "module_instance_mapping": {
                "KNMIUUR278": {
                    "Eref.d": "im.wiwb.knmi",
                    "Q.G": "im.wiwb.knmi",
                    "H.B": "im.wiwb.knmi",
                },
                "WS000323": {
                    "Eref.d": "im.wiwb.knmi",
                    "Q.G": "im.wiwb.knmi",
                    "H.B": "im.wiwb.knmi",
                },
            },
        },
    ),
    "hdsr": FEWSServiceConfig(
        name="HDSR",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHDSR",
        db_path="data/HDSR_wis.db3",
        test_data={
            "location_filters": ["gouda", "utrecht", "leiden"],
            "location_ids": ["beg_109", "beg_110"],
            "parameter_ids": ["BG.b.0", "H.G", "GW.G"],
            "parameter_filters": ["groundwater", "level", "GW.G"],
            "validated_combinations": [
                {
                    "location_id": "beg_109",
                    "parameter_id": "BG.b.0",
                    "module_instance_id": "ImportBegroeiingsMonitoring",
                },
            ],
            # Test cases for multiple locations/parameters
            "multiple_location_test": {
                "parameter_id": "BG.b.0",
                "location_id": ["beg_109", "beg_110"],
                "description": "Single parameter with multiple locations",
            },
            "multiple_parameter_test": {
                "parameter_id": ["BG.b.0", "H.G", "GW.G"],
                "location_id": "beg_109",
                "description": "Multiple parameters with single location",
            },
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
            # Module instance mapping for test combinations
            "module_instance_mapping": {
                "beg_109": {
                    "BG.b.0": "ImportBegroeiingsMonitoring",
                    "H.G": "ImportBegroeiingsMonitoring",
                    "GW.G": "ImportBegroeiingsMonitoring",
                },
                "beg_110": {
                    "BG.b.0": "ImportBegroeiingsMonitoring",
                    "H.G": "ImportBegroeiingsMonitoring",
                    "GW.G": "ImportBegroeiingsMonitoring",
                },
            },
        },
    ),
    "wsvv": FEWSServiceConfig(
        name="WSVV",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesWSVV",
        db_path="data/WSDD_wis.db3",
        test_data={
            "location_filters": ["den_haag", "delft", "zoetermeer"],
            "location_ids": [
                "HL000141",
                "HL000005",
                "HL000041",
            ],  # Updated with working locations that have data
            "parameter_ids": [
                "EV.15",
                "EV.hrsfi.m",
                "EV.lrsfi.m",
            ],  # Updated with working parameters that have data
            "parameter_filters": ["discharge", "temperature", "H.B"],
            "validated_combinations": [
                {
                    "location_id": "HL000141",
                    "parameter_id": "EV.15",
                    "module_instance_id": "Validatie",
                },  # 577 values (all flagged but real data)
                {
                    "location_id": "HL000005",
                    "parameter_id": "EV.15",
                    "module_instance_id": "Validatie",
                },  # 577 values (all flagged but real data)
                {
                    "location_id": "HL000041",
                    "parameter_id": "EV.15",
                    "module_instance_id": "Validatie",
                },  # 577 values (all flagged but real data)
            ],
            # Test cases for multiple locations/parameters
            "multiple_location_test": {
                "parameter_id": "EV.15",
                "location_id": ["HL000141", "HL000005", "HL000041"],
                "description": "Single parameter with multiple locations",
            },
            "multiple_parameter_test": {
                "parameter_id": ["EV.15", "EV.hrsfi.m", "EV.lrsfi.m"],
                "location_id": "HL000141",
                "description": "Multiple parameters with single location",
            },
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2024-01-01T00:00:00+01:00",
            "end_time": "2025-01-14T00:00:00+01:00",
            # Module instance mapping for test combinations
            "module_instance_mapping": {
                "HL000141": {
                    "EV.15": "Validatie",
                    "EV.hrsfi.m": "Validatie",
                    "EV.lrsfi.m": "Validatie",
                },
                "HL000005": {
                    "EV.15": "Validatie",
                    "EV.hrsfi.m": "Validatie",
                    "EV.lrsfi.m": "Validatie",
                },
                "HL000041": {
                    "EV.15": "Validatie",
                    "EV.hrsfi.m": "Validatie",
                    "EV.lrsfi.m": "Validatie",
                },
            },
        },
    ),
    "hhd": FEWSServiceConfig(
        name="HHD",
        web_service_url="http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHHD",
        db_path="data/HDSR_wis.db3",  # Use working database until HHD database is fixed
        test_data={
            "location_filters": ["hoorn", "heerhugowaard", "den_helder"],
            "location_ids": [
                "HHD_150183-pomp1",  # Put working location first
                "HHD_350101",
                "HHD_150183",
            ],  # Real location IDs from web service
            "parameter_ids": [
                "pompstatus.bedrijf",  # Put working parameter first
                "Q.meting",
                "Q.sim",
            ],  # Real parameter IDs with data
            "parameter_filters": ["water", "level", "Eref.d"],
            # Validated location-parameter combinations that have time series data
            "validated_combinations": [
                {
                    "location_id": "HHD_150183-pomp1",
                    "parameter_id": "pompstatus.bedrijf",
                    "module_instance_id": "ImportSphAbb",
                },  # 8641 values (all flagged but real data)
                {
                    "location_id": "HHD_150183",
                    "parameter_id": "Q.meting",
                    "module_instance_id": "ImportSphAbb",
                },  # 9 series
                {
                    "location_id": "HHD_350101",
                    "parameter_id": "Q.sim",
                    "module_instance_id": "ImportSphAbb",
                },  # 1 series
            ],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
            # Module instance mapping for test combinations
            "module_instance_mapping": {
                "HHD_150183-pomp1": {
                    "pompstatus.bedrijf": "ImportSphAbb",
                    "Q.meting": "ImportSphAbb",
                    "Q.sim": "ImportSphAbb",
                },
                "HHD_350101": {
                    "pompstatus.bedrijf": "ImportSphAbb",
                    "Q.meting": "ImportSphAbb",
                    "Q.sim": "ImportSphAbb",
                },
                "HHD_150183": {
                    "pompstatus.bedrijf": "ImportSphAbb",
                    "Q.meting": "ImportSphAbb",
                    "Q.sim": "ImportSphAbb",
                },
            },
        },
    ),
    "scheldestromen": FEWSServiceConfig(
        name="Scheldestromen",
        web_service_url="https://data.hkvfewsscheldestromen.nl:8443/FewsWebServices",
        db_path="data/HDSR_wis.db3",  # Use working database until Scheldestromen database is fixed
        test_data={
            "location_filters": ["terneuzen", "vlissingen", "antwerpen"],
            "location_ids": [
                "VOV9345",
                "VOV9346",
                "VOV32379",
            ],  # Real location IDs from web service
            "parameter_ids": [
                "WNSHDB1",
                "WNSHDB3",
                "Q.meting",
            ],  # Real parameter IDs with data
            "parameter_filters": ["water", "tide", "Q.G"],
            "validated_combinations": [
                {
                    "location_id": "VOV9345",
                    "parameter_id": "WNSHDB1",
                    "module_instance_id": "Productie",
                },
                {
                    "location_id": "VOV9345",
                    "parameter_id": "WNSHDB3",
                    "module_instance_id": "Productie",
                },
            ],
            "expected_location_count": 6,
            "expected_parameter_count": 6,
            "start_time": "2020-01-01T00:00:00+01:00",
            "end_time": "2024-12-31T23:59:59+01:00",
            # Module instance mapping for test combinations
            "module_instance_mapping": {
                "VOV9345": {
                    "WNSHDB1": "Productie",
                    "WNSHDB3": "Productie",
                    "Q.meting": "Productie",
                },
                "VOV9346": {
                    "WNSHDB1": "Productie",
                    "WNSHDB3": "Productie",
                    "Q.meting": "Productie",
                },
                "VOV32379": {
                    "WNSHDB1": "Productie",
                    "WNSHDB3": "Productie",
                    "Q.meting": "Productie",
                },
            },
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
