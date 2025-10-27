import requests
import httpx
from datetime import datetime
from typing import Tuple, Optional
from talk_with_fews.utils.utils import format_datetime
from talk_with_fews.utils.logging_utils import logger


def get_request(
    url: str,
    params: dict,
    mime_type: str = "text",
    timeout: float = 60.0,
    path_certificate: str = None,
):
    """
    Fetch data from the given URL.

    Args:
        url (str): URL address
        params (dict): list of URL parameters.
        mime_type (str, optional): MIME type. Default value is "text".
        timeout (float, optional): time before the connection is terminated (in seconds). Default value is 10.0 seconds.
        path_certificate (str, optional): path to a PEM file

    Returns:
        status: status code of the HTTP request
        data: data as text or JSON
    """
    data = None
    result = None

    try:
        headers = {}
        if mime_type == "json":
            # Zet de 'Accept' header naar application/json
            headers = {"Accept": "application/json"}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            if mime_type == "json":
                data = response.json()
            elif mime_type == "NETCDF":
                data = response
            else:
                data = response.text
        else:
            data = None
            result = response.text

    except Exception as error:
        result = error

    # Geef resultaat terug
    return result, data


def post_request(url: str, json: dict, mime_type: str = "text", timeout: float = 60.0):
    """
    Fetch data from the given URL via a POST request.

    Args:
        url (str): URL address.
        json (dict): JSON payload to include in the POST request.
        mime_type (str, optional): MIME type. Default value is "text".
        timeout (float, optional): Time before the connection is terminated (in seconds). Default value is 60.0 seconds.
    Returns:
        status: Status code of the HTTP POST request.
        data: Data as text or JSON.
    """
    data = None
    result = None

    with httpx.Client() as client:
        try:
            response = client.post(url=url, json=json, timeout=timeout)

            if response.status_code == httpx.codes.OK:
                if mime_type == "json":
                    data = response.json()
                else:
                    data = response.text
            else:
                data = None
                result = response.text

        except httpx.RequestError as error:
            result = error

    # Geef resultaat terug
    return result, data


def get_timeseries_headers(
    webservice_url: str,
    parameter_id: Optional[str] = None,
    location_id: Optional[str] = None,
    module_instance_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    show_statistics: bool = False,
    document_format: str = "PI_XML",  # Add format selection: PI_XML or PI_CSV
) -> Tuple[Optional[str], Optional[str], float]:
    """
    Robustly fetch timeseries headers from FEWS webservice with comprehensive error handling.

    This function provides a more robust alternative to the basic webservice calls,
    with better error handling and parameter validation.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_id: Parameter ID to query for (optional)
        location_id: Location ID to query for (optional)
        module_instance_id: Module instance ID to filter by (optional)
        start_time: Start time for the query (optional)
        end_time: End time for the query (optional)
        show_statistics: Whether to include statistics in the response

    Returns:
        Tuple of (error, xml_content) where error is None on success

    Raises:
        ValueError: For invalid input parameters or unexpected errors
    """

    # Validate input - must have either parameter_id or location_id, or both for batched queries
    # Allow both to be None for discovering all available series
    if not parameter_id and not location_id:
        # This is allowed for discovering all available series
        pass

    # Construct request URL and parameters
    request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
    params = {
        "onlyHeaders": "True",
        "documentFormat": document_format,  # Use the selected format (PI_XML or PI_CSV)
    }

    # Add parameter and location filters (both can be specified for batched queries)
    if parameter_id:
        params["parameterIds"] = parameter_id
        query_type = f"parameter {parameter_id}"
    if location_id:
        params["locationIds"] = location_id
        if parameter_id:
            query_type += f" with locations {location_id}"
        else:
            query_type = f"location {location_id}"

    # If neither parameter_id nor location_id is specified, query all available series
    if not parameter_id and not location_id:
        query_type = "all available series"

    # Add optional parameters
    if module_instance_id:
        params["moduleInstanceIds"] = module_instance_id

    if start_time:
        params["startTime"] = format_datetime(start_time)

    if end_time:
        params["endTime"] = format_datetime(end_time)

    if show_statistics:
        params["showStatistics"] = "true"

    # Log the request URL for debugging
    logger.info(f"🌐 Making request to: {request_url}")
    logger.info(f"📋 Parameters: {params}")

    # Make the request with timing
    import time

    start_time = time.time()
    error, data = get_request(request_url, params=params)
    request_time = time.time() - start_time

    logger.info(f"⏱️  Request completed in {request_time:.2f} seconds")
    if data:
        logger.info(f"📄 Response size: {len(data)} characters")

    if error is not None:
        # Handle expected "no data" responses as normal, not errors
        error_str = str(error)
        if (
            "No timeSeries found" in error_str
            or "Some of the parameters do not exists" in error_str
            or "Some of the location ids do not exist" in error_str
        ):
            # Return None for expected no-data scenarios
            logger.info(f"No time series found for {query_type}")
            return None, None, request_time
        elif (
            "HTTP Status 500 – Internal Server Error" in error_str
            and "java.lang.OutOfMemoryError" in error_str
        ):
            logger.info(
                f"No time series found for {query_type} (500 Internal Server Error)"
            )
            return "OutofMemory", None, request_time
        else:
            # Log unexpected errors and re-raise
            logger.error(f"Error fetching series headers for {query_type}: {error}")
            raise ValueError(f"Error fetching series headers for {query_type}: {error}")

    logger.info(
        f"Successfully fetched series headers for {query_type} in {document_format} format"
    )
    return None, data, request_time


def get_timeseries_data(
    webservice_url: str,
    parameter_id: Optional[str] = None,
    location_id: Optional[str] = None,
    module_instance_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    document_format: str = "PI_CSV",
) -> Tuple[Optional[str], Optional[str], float]:
    """
    Fetch actual time series data (not just headers) from FEWS webservice.

    This function is optimized for retrieving time series data, using CSV format
    for better performance when dealing with large datasets.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_id: Parameter ID to query for (optional)
        location_id: Location ID to query for (optional)
        module_instance_id: Module instance ID to filter by (optional)
        start_time: Start time for data retrieval (optional)
        end_time: End time for data retrieval (optional)
        document_format: Format for data retrieval ("PI_CSV" recommended for data)

    Returns:
        Tuple of (error, data, request_time)
    """
    # Validate inputs
    if not parameter_id and not location_id:
        raise ValueError("Must specify either parameter_id or location_id")

    # Construct request URL and parameters
    request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
    params = {
        "documentFormat": document_format,
        # Note: No onlyHeaders parameter - we want the actual data
    }

    # Add location or parameter filter
    if parameter_id:
        params["parameterIds"] = parameter_id
        query_type = f"parameter {parameter_id}"
    elif location_id:
        params["locationIds"] = location_id
        query_type = f"location {location_id}"

    # Add optional filters
    if module_instance_id:
        params["moduleInstanceIds"] = module_instance_id

    if start_time:
        params["startTime"] = format_datetime(start_time)

    if end_time:
        params["endTime"] = format_datetime(end_time)

    # Log the request URL for debugging
    logger.info(f"🌐 Making data request to: {request_url}")
    logger.info(f"📋 Parameters: {params}")

    # Make the request with timing
    import time

    start_time_req = time.time()
    error, data = get_request(request_url, params=params)
    request_time = time.time() - start_time_req

    logger.info(f"⏱️  Data request completed in {request_time:.2f} seconds")
    if data:
        logger.info(f"📄 Response size: {len(data)} characters")

    if error is not None:
        # Handle expected "no data" responses as normal, not errors
        error_str = str(error)
        if (
            "no data" in error_str.lower()
            or "not found" in error_str.lower()
            or "empty" in error_str.lower()
        ):
            logger.info(f"No time series data found for {query_type}")
            return None, None, request_time
        else:
            # Log unexpected errors and re-raise
            logger.error(f"Error fetching time series data for {query_type}: {error}")
            raise ValueError(
                f"Error fetching time series data for {query_type}: {error}"
            )

    logger.info(
        f"Successfully fetched time series data for {query_type} in {document_format} format"
    )
    return None, data, request_time
