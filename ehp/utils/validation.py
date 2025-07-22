import re
import html
import logging
from typing import Any, Dict

from fastapi import HTTPException, Request
from pydantic import BaseModel, validator

from ehp.utils.base import log_error


class InputSanitizer:
    """Simple input sanitization"""

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Basic string sanitization"""
        if not isinstance(value, str):
            return value

        # Remove HTML tags and escape remaining content
        value = re.sub(r"<[^>]+>", "", value)
        # HTML escape breaks any implementation that expects strings
        # with valid escapeable characters, so we skip it
        # TODO: Revisit this decision
        # value = html.escape(value)

        # Remove dangerous patterns
        dangerous_patterns = [
            r"javascript:",
            r"on\w+\s*=",
            r"<script",
            r"</script>",
            r"vbscript:",
            r"data:text/html",
        ]

        for pattern in dangerous_patterns:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        return value.strip()

    @staticmethod
    def check_sql_injection(value: str) -> bool:
        """Check for very obvious SQL injection patterns only"""
        if not isinstance(value, str):
            return False

        # Only catch the most blatant injection attempts
        sql_patterns = [
            # Classic union select attacks
            r"\bunion\s+(all\s+)?select\b",
            # SQL comments used to terminate queries
            r'[;\'"]\s*-{2,}',
            # Drop table attacks
            r"\bdrop\s+table\b",
            # Obvious tautologies
            r"\bor\s+1\s*=\s*1\b",
            r"\band\s+1\s*=\s*2\b",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False


class ValidatedModel(BaseModel):
    """Base model with automatic sanitization"""

    def __init__(self, **data):
        # Sanitize string fields before validation
        for field_name, value in data.items():
            if isinstance(value, str):
                # Check for SQL injection
                if InputSanitizer.check_sql_injection(value):
                    raise ValueError(f"Dangerous pattern detected in {field_name}")

                # Sanitize the value
                data[field_name] = InputSanitizer.sanitize_string(value)

        super().__init__(**data)


class RequestValidator:
    """Request validator with sanitization"""

    def __init__(self):
        self.logger = logging.getLogger("ehp.validation")

    def validate_request_data(
        self, data: Dict[str, Any], model_class: BaseModel = None
    ) -> Dict[str, Any]:
        """Validate and sanitize request data"""
        result = {"is_valid": True, "errors": [], "sanitized_data": {}, "warnings": []}

        try:
            # Sanitize all string values
            sanitized_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Check for dangerous patterns
                    if InputSanitizer.check_sql_injection(value):
                        result["is_valid"] = False
                        result["errors"].append(f"Security violation in field: {key}")
                        continue

                    sanitized_data[key] = InputSanitizer.sanitize_string(value)
                else:
                    sanitized_data[key] = value

            result["sanitized_data"] = sanitized_data

            # Validate with Pydantic model if provided
            if model_class and result["is_valid"]:
                try:
                    validated_model = model_class(**sanitized_data)
                    result["validated_model"] = validated_model
                except Exception as e:
                    result["is_valid"] = False
                    result["errors"].append(str(e))

        except Exception as e:
            result["is_valid"] = False
            result["errors"].append(f"Validation error: {str(e)}")
            log_error(f"Validation error: {e}")

        return result


# Global validator instance
validator = RequestValidator()


def validate_and_sanitize(model_class: BaseModel = None):
    """Dependency for request validation"""

    async def validate_request(request: Request):
        # Extract request data
        data = {}

        # Get query params
        data.update(dict(request.query_params))

        # Get body data for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    data.update(body)
            except Exception as e:
                # This catches most exceptions but not KeyboardInterrupt, SystemExit, etc.
                logging.getLogger("ehp.validation").debug(
                    f"Failed to parse request body: {e}"
                )

        # Validate and sanitize
        validation_result = validator.validate_request_data(data, model_class)

        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Request validation failed",
                    "errors": validation_result["errors"],
                },
            )

        # Store results in request state
        request.state.validation_result = validation_result
        return validation_result["sanitized_data"]

    return validate_request


def summarize_text(content: str, max_length: int, ellipsis: str = "...") -> str:
    """Summarize a given text to a specified maximum length."""
    if len(content) <= max_length:
        return content
    return content[: max_length - len(ellipsis)] + ellipsis
