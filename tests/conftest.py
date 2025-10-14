"""
pytest configuration and fixtures for FEWS testing.

This module provides pytest fixtures that automatically handle
FEWS service configuration following the Altair pattern.
"""

import pytest
import os
from tests.test_config import get_test_service_config


# =============================================================================
# Test Configuration and Fixtures (Following Altair Pattern)
# =============================================================================

# Service parameters for parametrized testing
_service_params = {
    "actueelwaterbeeld": pytest.param("actueelwaterbeeld"),
    "hdsr": pytest.param("hdsr"),
    "wsvv": pytest.param("wsvv"),
    "hhd": pytest.param("hhd"),
    "scheldestromen": pytest.param("scheldestromen"),
}

# Custom pytest markers for different service groups
fews_services: pytest.MarkDecorator = pytest.mark.parametrize(
    "service", _service_params.values()
)

fews_services_production: pytest.MarkDecorator = pytest.mark.parametrize(
    "service", [_service_params["actueelwaterbeeld"]]
)

fews_services_local: pytest.MarkDecorator = pytest.mark.parametrize(
    "service", [v for k, v in _service_params.items() if k != "actueelwaterbeeld"]
)

fews_services_hdsr_wsvv: pytest.MarkDecorator = pytest.mark.parametrize(
    "service", [_service_params["hdsr"], _service_params["wsvv"]]
)

fews_services_water_boards: pytest.MarkDecorator = pytest.mark.parametrize(
    "service",
    [_service_params["hdsr"], _service_params["wsvv"], _service_params["hhd"]],
)


@pytest.fixture(scope="session")
def fews_service():
    """
    Get the FEWS service configuration for the current test session.

    This fixture automatically determines which FEWS service to use based on:
    1. FEWS_TEST_SERVICE environment variable
    2. CI environment detection
    3. Default to actueelwaterbeeld
    """
    return get_test_service_config()


@pytest.fixture
def fews_service_by_name(service: str):
    """
    Get FEWS service configuration by name.

    This fixture is used with the parametrized markers above.
    """
    os.environ["FEWS_TEST_SERVICE"] = service
    return get_test_service_config()


@pytest.fixture
def fews_user_settings(fews_service_by_name):
    """
    Get user settings configured for the current FEWS service.
    """
    from tests.utils_tests import setup_dot_env

    return setup_dot_env()


@pytest.fixture
def fews_test_data(fews_service_by_name):
    """
    Get test data for the current FEWS service.
    """
    return fews_service_by_name.test_data


# Helper fixtures for common test data
@pytest.fixture
def fews_location_filter(fews_test_data):
    """Get location filter for current service."""
    return fews_test_data["location_filters"][0]


@pytest.fixture
def fews_location_id(fews_test_data):
    """Get location ID for current service."""
    return fews_test_data["location_ids"][0]


@pytest.fixture
def fews_parameter_id(fews_test_data):
    """Get parameter ID for current service."""
    return fews_test_data["parameter_ids"][0]


@pytest.fixture
def fews_expected_location_count(fews_test_data):
    """Get expected location count for current service."""
    return fews_test_data["expected_location_count"]


@pytest.fixture
def fews_expected_parameter_count(fews_test_data):
    """Get expected parameter count for current service."""
    return fews_test_data["expected_parameter_count"]
