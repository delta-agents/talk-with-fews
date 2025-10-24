"""
Parallel testing decorator for FEWS services.

This decorator allows individual test functions to run in parallel
against different FEWS services while maintaining explicit test names.
"""

import pytest
import os
from functools import wraps


def fews_parallel(*services):
    """
    Decorator to run a test function in parallel against multiple FEWS services.
    Automatically detects CI and only runs against production service in CI.

    Usage:
        @fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen", "wsdd")
        def test_get_locations(service):
            # In CI: only runs against "actueelwaterbeeld"
            # Locally: runs against all 5 services
            pass

    Args:
        *services: List of service names to test against (CI will only use first one)
    """

    def decorator(test_func):
        @wraps(test_func)
        def wrapper(service, *args, **kwargs):
            # Store the original value to restore later
            original_service = os.environ.get("FEWS_TEST_SERVICE")

            try:
                # Set the service explicitly for this test instance
                os.environ["FEWS_TEST_SERVICE"] = service

                # Call the original test function with just the service parameter
                return test_func(service, *args, **kwargs)
            finally:
                # Restore the original value
                if original_service is not None:
                    os.environ["FEWS_TEST_SERVICE"] = original_service
                else:
                    os.environ.pop("FEWS_TEST_SERVICE", None)

        # Check if running in CI
        is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

        if is_ci:
            # In CI, only run against the first service (should be actueelwaterbeeld)
            services_to_use = [services[0]] if services else []
        else:
            # Locally, run against all services
            services_to_use = services

        # Mark the test for parallel execution
        wrapper = pytest.mark.parametrize("service", services_to_use)(wrapper)
        return wrapper

    return decorator
