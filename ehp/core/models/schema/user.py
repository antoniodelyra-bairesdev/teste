from pydantic import BaseModel, Field, field_validator, ConfigDict, AfterValidator
from datetime import datetime
from typing import Annotated
from ehp.core.models.schema.registration import check_password_strength
from ehp.utils.validation import ValidatedModel

import re


class UserProfileUpdateSchema(BaseModel):
    """Schema for updating user profile information."""

    full_name: str = Field(
        ..., min_length=1, max_length=250, description="User's full name"
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class UserProfileResponseSchema(BaseModel):
    """Schema for user profile response."""

    id: int
    full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordChangeSchema(BaseModel):
    """Schema for changing user password."""

    current_password: str = Field(..., description="Current password")
    new_password: Annotated[
        str,
        Field(..., description="New password"),
        AfterValidator(check_password_strength),
    ]
    confirm_password: Annotated[
        str,
        Field(..., description="Confirm new password"),
        AfterValidator(check_password_strength),
    ]

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordChangeResponseSchema(BaseModel):
    """Schema for password change response."""

    message: str
    code: int


class UpdatePasswordSchema(ValidatedModel):
    """Schema for updating user password."""

    new_password: Annotated[str, AfterValidator(check_password_strength)]
    reset_token: Annotated[
        str,
        Field(
            ...,
            description="Password reset token",
            pattern=re.compile(r"^[a-fA-F0-9]{64}$"),
        ),
    ]
    logout: bool = False
