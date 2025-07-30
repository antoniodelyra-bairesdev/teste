from typing import Optional, List
import re
from datetime import datetime
from typing import Annotated, Any, Dict

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from ehp.core.models.schema.registration import check_password_strength
from ehp.utils.constants import (
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
)
from ehp.utils.validation import ValidatedModel


class UserDisplayNameUpdateSchema(ValidatedModel):
    """
    Schema for updating user display name.

    Validates display name format, length, and character restrictions.
    Display name must be unique across all users and follow specified format.
    """

    display_name: str = Field(
        description="The new display name for the user",
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """
        Validate and clean display name.

        Args:
            v: The display name to validate

        Returns:
            The cleaned display name

        Raises:
            ValueError: If display name is invalid
        """
        if not v or not v.strip():
            raise ValueError("Display name is required")

        # Remove extra whitespace
        v = v.strip()

        # Check length constraints with custom error messages
        if len(v) < DISPLAY_NAME_MIN_LENGTH:
            raise ValueError(
                f"Display name must be at least {DISPLAY_NAME_MIN_LENGTH} "
                "characters long"
            )

        if len(v) > DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(
                f"Display name must be no more than {DISPLAY_NAME_MAX_LENGTH} "
                "characters long"
            )

        # Check for spaces (not allowed)
        if " " in v:
            raise ValueError("Display name cannot contain spaces")

        # Check for valid characters (letters, numbers, hyphens, underscores, dots)
        if not re.match(r"^[a-zA-Z0-9\-_\.À-ÿ]+$", v):
            raise ValueError(
                "Display name can only contain letters, numbers, hyphens, "
                "underscores, and dots"
            )

        return v


class UserDisplayNameResponseSchema(ValidatedModel):
    """
    Schema for display name update response.

    Contains the updated user information and success message.
    """

    id: int = Field(description="The user ID")
    display_name: str = Field(description="The updated display name")
    message: str = Field(
        default="Display name updated successfully", description="Success message"
    )


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
            ..., description="Password reset token",
            pattern=re.compile(r"^[a-fA-F0-9]{64}$"),
        ),
    ]
    logout: bool = False


class EmailChangeRequestSchema(ValidatedModel):
    """Schema for requesting email change."""

    new_email: str

    @field_validator("new_email")
    @classmethod
    def validate_email(cls, v: str):
        if not v or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Valid email address is required")
        return v.strip().lower()


class EmailChangeConfirmSchema(ValidatedModel):
    """Schema for confirming email change."""

    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str):
        if not v or len(v.strip()) == 0:
            raise ValueError("Token is required")
        return v.strip()


class EmailChangeResponseSchema(ValidatedModel):
    """Response schema for email change operations."""

    message: str
    code: int


class UpdateUserSettings(ValidatedModel):
    """Schema for updating user settings."""

    readability_preferences: Dict[str, Any] | None = None
    email_notifications: bool | None = None


class AvatarUploadResponseSchema(BaseModel):
    """Schema for avatar upload response."""
    avatar_url: str = Field(..., description="URL of the uploaded avatar")
    message: str = Field(..., description="Success message")


class UserCategoriesUpdateSchema(BaseModel):
    """Schema for updating user preferred news categories."""
    category_ids: List[int] = Field(..., description="List of news category IDs")

    @field_validator('category_ids')
    @classmethod
    def validate_category_ids(cls, v):
        if not isinstance(v, list):
            raise ValueError("Category IDs must be a list")

        # Remove duplicates while preserving order
        unique_ids = []
        for category_id in v:
            if category_id not in unique_ids:
                unique_ids.append(category_id)

        return unique_ids


class UserCategoriesResponseSchema(BaseModel):
    """Schema for user categories response."""
    id: int
    full_name: str
    preferred_news_categories: Optional[List[int]] = Field(default=None, description="List of preferred news category IDs")

    model_config = ConfigDict(from_attributes=True)

class OnboardingStatusResponseSchema(BaseModel):
    """Schema for onboarding status response."""
    onboarding_complete: bool
