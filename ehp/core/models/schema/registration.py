import re
from typing import Annotated
from pydantic import AfterValidator, field_validator

from ehp.utils.validation import ValidatedModel

_special_characters_pattern = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/;'`~]")


def check_password_strength(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    if not _special_characters_pattern.search(password):
        raise ValueError("Password must contain at least one special character")

    return password


class RegistrationSchema(ValidatedModel):
    """Simple enhanced registration model"""

    user_name: str
    user_email: str
    user_password: Annotated[str, AfterValidator(check_password_strength)]

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, v: str):
        if not v:
            raise ValueError("Email is required")

        # Remove spaces and convert to lowercase
        v = v.strip().lower()

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("user_name")
    @classmethod
    def validate_name(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Name is required")
        return v.strip()
