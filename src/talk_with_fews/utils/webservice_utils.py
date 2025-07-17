import requests
import httpx


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
