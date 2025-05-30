from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from cuid import cuid
from fastapi.responses import JSONResponse


def make_response(
    response_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    pagination_data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> JSONResponse:
    """
    Use this function to create a standard response object for the API.
    :param response_data: any dict related reponse data.
    :param pagination_data: any dict related to pagination data.
    :param status_code: status code of the response.
    :return: reshaped response object.
    """
    return JSONResponse(
        {
            "result": response_data,
            "pagination": pagination_data if pagination_data else {},
            "response_id": cuid(),
            "response_time": str(datetime.now().isoformat()),
        },
        status_code,
    )
