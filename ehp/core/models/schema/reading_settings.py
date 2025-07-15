from typing import Optional

from pydantic import Field

from ehp.utils.validation import ValidatedModel


class FontSettings(ValidatedModel):
    """Font settings for different text types."""

    headline: str = Field(default="System", description="Font for headlines")
    body: str = Field(default="System", description="Font for body text")
    caption: str = Field(default="System", description="Font for captions")


class ReadingSettings(ValidatedModel):
    """Complete reading settings configuration."""

    font_size: str = Field(default="Medium", description="Font size setting")
    fonts: FontSettings = Field(
        default_factory=FontSettings, description="Font family settings"
    )
    font_weight: str = Field(default="Normal", description="Font weight setting")
    line_spacing: str = Field(default="Standard", description="Line spacing setting")
    color_mode: str = Field(default="Default", description="Color mode setting")


class ReadingSettingsUpdate(ValidatedModel):
    """Reading settings update schema - all fields optional."""

    font_size: Optional[str] = Field(None, description="Font size setting")
    fonts: Optional[FontSettings] = Field(None, description="Font family settings")
    font_weight: Optional[str] = Field(None, description="Font weight setting")
    line_spacing: Optional[str] = Field(None, description="Line spacing setting")
    color_mode: Optional[str] = Field(None, description="Color mode setting")
