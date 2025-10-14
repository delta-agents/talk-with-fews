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

    Usage:
        # For local testing - all services
        @fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
        def test_get_locations(service):
            pass

        # For GitHub Actions - production only
        @fews_parallel("actueelwaterbeeld")
        def test_get_locations(service):
            pass

    Args:
        *services: List of service names to test against
    """

    def decorator(test_func):
        @wraps(test_func)
        def wrapper(service, *args, **kwargs):
            # Set the service explicitly
            os.environ["FEWS_TEST_SERVICE"] = service

            # Call the original test function with just the service parameter
            return test_func(service, *args, **kwargs)

        # Mark the test for parallel execution
        wrapper = pytest.mark.parametrize("service", services)(wrapper)
        return wrapper

    return decorator
