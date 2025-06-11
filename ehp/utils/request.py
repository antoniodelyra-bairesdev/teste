from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from cuid import cuid
from fastapi.responses import JSONResponse
from fastapi import HTTPException, Request

from ehp.config import settings
from ehp.utils.base import log_info


def make_response(
    response_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    pagination_data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    request: Optional[Request] = None,
    include_metadata: bool = True,
) -> JSONResponse:
    """
    Enhanced response creation with detailed tracking and logging
    """

    response_metadata = {
        "response_id": cuid(),
        "response_time": datetime.now().isoformat(),
        "status_code": status_code,
    }

    if include_metadata and request:
        # Add request tracking information
        response_metadata.update(
            {
                "request_id": getattr(request.state, "request_id", None),
                "request_path": request.url.path,
                "request_method": request.method,
                "client_ip": getattr(request.client, "host", "unknown"),
                "user_agent": request.headers.get("user-agent", "unknown")[
                    :100
                ],  # Truncate user agent
            }
        )

        # Include validation results if available
        if hasattr(request.state, "validation_results"):
            validation_results = request.state.validation_results
            response_metadata["validation_status"] = (
                "passed" if validation_results["is_valid"] else "failed"
            )
            if validation_results["warnings"]:
                response_metadata["validation_warnings"] = len(
                    validation_results["warnings"]
                )

    # Build response
    response_body = {
        "result": response_data,
        "pagination": pagination_data if pagination_data else {},
        "metadata": response_metadata,
    }

    # Log response if enabled
    if settings.DEBUG or getattr(settings, "RESPONSE_LOGGING_ENABLED", False):
        log_info(
            f"Response created: {response_metadata['response_id']} | Status: {status_code}"
        )

    return JSONResponse(response_body, status_code)
