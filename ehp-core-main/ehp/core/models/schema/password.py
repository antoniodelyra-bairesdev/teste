import re
from typing import Optional

from pydantic import field_validator

from ehp.utils.validation import ValidatedModel


class PasswordSchema(ValidatedModel):
    """Simple enhanced password model"""
    auth_id: Optional[int] = None
    user_email: Optional[str] = None
    user_password: Optional[str] = None
    old_password: Optional[str] = None
    reset_code: Optional[str] = None

    @field_validator("reset_code")
    def validate_reset_code(cls, v):
        if v and not re.match(r"^\d{4}$", v):
            raise ValueError("Reset code must be 4 digits")
        return v
