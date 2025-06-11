import re
from pydantic import field_validator

from ehp.utils.validation import ValidatedModel


class RegistrationSchema(ValidatedModel):
    """Simple enhanced registration model"""

    user_name: str
    user_email: str
    user_password: str

    @field_validator("user_email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")

        # Remove spaces and convert to lowercase
        v = v.strip().lower()

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("user_name")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Name is required")
        return v.strip()

    @field_validator("user_password")
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        return v
