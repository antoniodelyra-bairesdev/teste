from fastapi import Request
from fastapi.responses import ORJSONResponse
from ehp.utils.base import log_error

def default_error_handler(request: Request, _: Exception) -> ORJSONResponse:
    del request  # Unused parameter, but kept for compatibility
    log_error("An unexpected error occurred")
    return ORJSONResponse({"detail": "Internal server error"}, status_code=500)
