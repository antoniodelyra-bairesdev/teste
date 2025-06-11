import re
from typing import Optional

from pydantic import field_validator

from ehp.utils.validation import ValidatedModel
from ehp.core.models.schema.registration import RegistrationSchema


class PasswordSchema(ValidatedModel):
    """Simple enhanced password model"""

    auth_id: Optional[int] = None
    user_email: Optional[str] = None
    user_password: Optional[str] = None
    old_password: Optional[str] = None
    reset_code: Optional[str] = None

    @field_validator("reset_code")
    @classmethod
    def validate_reset_code(cls, v):
        if v and not re.match(r"^\d{4}$", v):
            raise ValueError("Reset code must be 4 digits")
        return v


class PasswordResetConfirmSchema(ValidatedModel):
    """Schema for confirming a password reset."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """
        Validates the password according to the policy:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        """
        return RegistrationSchema.validate_password(v)


class PasswordResetResponse(ValidatedModel):
    """Response model for password reset confirmation."""

    message: str
    code: int


class PasswordResetRequestSchema(ValidatedModel):
    """Password reset request model"""
    user_email: str

    @field_validator("user_email")
    def validate_email(cls, v):
        if not v or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Valid email address is required")
        return v.lower()
