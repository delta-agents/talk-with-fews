"""
Discover all available series headers from FEWS webservice using async parallel processing.

This module provides high-performance bulk discovery of all available series headers
by querying the FEWS webservice in parallel. It's designed to be used during server
initialization to pre-populate the series headers cache.
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Tuple
from talk_with_fews.utils.logging_utils import logger


async def discover_all_series_headers_async(
    webservice_url: str,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    show_statistics: bool = True,
    max_concurrent: int = 20,
) -> Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
    """
    Async version for high-performance parallel processing of series headers discovery.

    Uses httpx.AsyncClient with connection pooling and HTTP/2 support for optimal
    performance when processing many parameters/locations in parallel.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        show_statistics: Whether to include statistics in the response
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Dictionary mapping request_key -> series_data where series_data contains
        all discovered series headers for that request
    """
    # Configure connection limits for optimal performance
    limits = httpx.Limits(
        max_connections=max_concurrent,
        max_keepalive_connections=max_concurrent,
        keepalive_expiry=30.0,
    )

    # Configure timeout
    timeout = httpx.Timeout(60.0, connect=10.0)

    results = {}

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        http2=True,  # Enable HTTP/2 for better multiplexing
    ) as client:

        async def fetch_series_headers(
            request_params: dict,
        ) -> Tuple[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
            """Fetch series headers for given parameters/locations."""
            try:
                # Construct request URL and parameters
                request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
                params = {
                    "onlyHeaders": "True",
                    "documentFormat": "PI_XML",
                }

                # Add parameter and location filters
                if request_params.get("parameter_ids"):
                    params["parameterIds"] = ",".join(request_params["parameter_ids"])
                if request_params.get("location_ids"):
                    params["locationIds"] = ",".join(request_params["location_ids"])
                if show_statistics:
                    params["showStatistics"] = "true"

                # Make async request
                response = await client.get(request_url, params=params)
                response.raise_for_status()

                xml_content = response.text
                logger.info(f"📄 Response size: {len(xml_content)} characters")

                # Parse XML and extract series headers
                series_headers = {}

                try:
                    root = ET.fromstring(xml_content)

                    # Find all series elements - try different namespace approaches
                    series_elements = root.findall(".//series")
                    if not series_elements:
                        # Try with namespace
                        series_elements = root.findall(
                            ".//{http://www.wldelft.nl/fews/PI}series"
                        )

                    logger.info(f"Found {len(series_elements)} series elements in XML")

                    for i, series in enumerate(series_elements):
                        # Extract series metadata from header element (not directly on series)
                        # Try both with and without namespace
                        header_elem = series.find("header")
                        if header_elem is None:
                            # Try with namespace
                            header_elem = series.find(
                                "{http://www.wldelft.nl/fews/PI}header"
                            )

                        if header_elem is None:
                            continue

                        # Try both with and without namespace for child elements
                        module_instance_id_elem = header_elem.find(
                            "moduleInstanceId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}moduleInstanceId"
                        )
                        location_id_elem = header_elem.find(
                            "locationId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}locationId"
                        )
                        parameter_id_elem = header_elem.find(
                            "parameterId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}parameterId"
                        )

                        # Extract text content from elements
                        module_instance_id = (
                            module_instance_id_elem.text
                            if module_instance_id_elem is not None
                            else None
                        )
                        location_id = (
                            location_id_elem.text
                            if location_id_elem is not None
                            else None
                        )
                        parameter_id = (
                            parameter_id_elem.text
                            if parameter_id_elem is not None
                            else None
                        )

                        if not all([module_instance_id, location_id, parameter_id]):
                            continue

                        # Extract time information from header element
                        # Note: We're not storing first_value_time and last_value_time
                        # as per user requirements

                        # Extract other metadata from header element
                        type_elem = header_elem.find("type") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}type"
                        )
                        series_type = type_elem.text if type_elem is not None else None

                        time_step_elem = header_elem.find(
                            "timeStep"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeStep")
                        time_step_unit = ""
                        time_step_multiplier = 1
                        if time_step_elem is not None:
                            time_step_unit = time_step_elem.get("unit") or ""
                            time_step_multiplier = time_step_elem.get("multiplier")
                            if time_step_multiplier:
                                try:
                                    time_step_multiplier = int(time_step_multiplier)
                                except ValueError:
                                    time_step_multiplier = 1
                            else:
                                time_step_multiplier = 1

                        miss_val_elem = header_elem.find("missVal") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}missVal"
                        )
                        miss_val = 0.0
                        if miss_val_elem is not None and miss_val_elem.text:
                            try:
                                miss_val = float(miss_val_elem.text)
                            except ValueError:
                                pass

                        time_zone_elem = header_elem.find(
                            "timeZone"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeZone")
                        time_zone = (
                            time_zone_elem.text
                            if time_zone_elem is not None and time_zone_elem.text
                            else ""
                        )

                        qualifiers_elem = header_elem.find(
                            "qualifiers"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}qualifiers"
                        )
                        qualifiers = (
                            qualifiers_elem.text
                            if qualifiers_elem is not None
                            else None
                        )

                        # Store the series header data
                        series_key = (module_instance_id, location_id, parameter_id)
                        series_headers[series_key] = {
                            "type": series_type,
                            "moduleInstanceId": module_instance_id,
                            "locationId": location_id,
                            "parameterId": parameter_id,
                            "timeStepUnit": time_step_unit,
                            "timeStepMultiplier": time_step_multiplier,
                            "missVal": miss_val,
                            "timeZone": time_zone,
                            "qualifiers": qualifiers,
                        }

                except ET.ParseError as e:
                    logger.error(f"Error parsing XML for request {request_params}: {e}")
                    return "error", {}
                except Exception as e:
                    logger.error(
                        f"Error processing series headers for request {request_params}: {e}"
                    )
                    return "error", {}

                # Create a key for the request (either parameter or location based)
                request_key = (
                    "params_" + "_".join(request_params.get("parameter_ids", []))
                    if request_params.get("parameter_ids")
                    else "locs_" + "_".join(request_params.get("location_ids", []))
                )

                logger.info(
                    f"Discovered {len(series_headers)} series headers for {request_key}"
                )
                return request_key, series_headers

            except Exception as e:
                logger.error(f"Error fetching series headers for {request_params}: {e}")
                return "error", {}

        # Process requests with controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(request_params: dict):
            async with semaphore:
                return await fetch_series_headers(request_params)

        # Create request tasks based on what we're processing
        tasks = []

        if parameter_ids:
            # Process each parameter individually for better granularity
            for param_id in parameter_ids:
                tasks.append(fetch_with_semaphore({"parameter_ids": [param_id]}))
        elif location_ids:
            # Process each location individually for better granularity
            for location_id in location_ids:
                tasks.append(fetch_with_semaphore({"location_ids": [location_id]}))
        else:
            # Process as a single batch request
            request_params = {}
            if parameter_ids:
                request_params["parameter_ids"] = parameter_ids
            if location_ids:
                request_params["location_ids"] = location_ids
            tasks.append(fetch_with_semaphore(request_params))

        # Execute all tasks concurrently
        logger.info(
            f"Starting async processing of {len(tasks)} requests with max {max_concurrent} concurrent requests"
        )
        start_time = datetime.now()

        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Completed async processing in {duration:.2f} seconds")

        # Process results
        for result in completed_tasks:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                continue

            request_key, series_headers = result
            results[request_key] = series_headers

    return results


def discover_all_series_headers_sync(
    webservice_url: str,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    show_statistics: bool = True,
    max_concurrent: int = 20,
) -> Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
    """
    Synchronous wrapper for the async series headers discovery function.

    This function handles the case where we're already in an event loop
    (like in FastAPI test environments) by using a separate thread.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        show_statistics: Whether to include statistics in the response
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Dictionary mapping request_key -> series_data where series_data contains
        all discovered series headers for that request
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # If we're in an event loop, we need to handle this differently
        import concurrent.futures

        # Run in a separate thread with its own event loop
        def run_in_thread():
            return asyncio.run(
                discover_all_series_headers_async(
                    webservice_url=webservice_url,
                    parameter_ids=parameter_ids,
                    location_ids=location_ids,
                    show_statistics=show_statistics,
                    max_concurrent=max_concurrent,
                )
            )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()

    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(
            discover_all_series_headers_async(
                webservice_url=webservice_url,
                parameter_ids=parameter_ids,
                location_ids=location_ids,
                show_statistics=show_statistics,
                max_concurrent=max_concurrent,
            )
        )
