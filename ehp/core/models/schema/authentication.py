import re
from typing import Optional

from pydantic import field_validator

from ehp.utils.validation import ValidatedModel


class AuthenticationSchema(ValidatedModel):
    """Simple enhanced authentication model"""

    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_pwd: str

    @field_validator("user_email")
    def validate_email(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v.lower() if v else v

    @field_validator("user_name")
    def validate_username(cls, v):
        if v and (len(v) < 3 or not re.match(r"^[a-zA-Z0-9_-]+$", v)):
            raise ValueError("Invalid username format")
        return v

    @field_validator("user_pwd")
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Password required and must be at least 8 characters")
        return v
