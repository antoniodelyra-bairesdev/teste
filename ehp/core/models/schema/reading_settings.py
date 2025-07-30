from enum import Enum

from pydantic import Field, field_validator
from ehp.utils.validation import ValidatedModel


class FontSize(str, Enum):
    """Font size options for reading settings."""

    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class FontWeight(str, Enum):
    """Font weight options for reading settings."""

    LIGHT = "Light"
    NORMAL = "Normal"
    BOLD = "Bold"


class LineSpacing(str, Enum):
    """Line spacing options for reading settings."""

    COMPACT = "Compact"
    STANDARD = "Standard"
    SPACIOUS = "Spacious"


class ColorMode(str, Enum):
    """Color mode options including accessibility presets."""

    DEFAULT = "Default"
    DARK = "Dark"
    RED_GREEN_COLORBLIND = "Red-Green Color Blindness"
    BLUE_YELLOW_COLORBLIND = "Blue-Yellow Color Blindness"


class FontOption(str, Enum):
    """Font family options for different text elements."""

    SYSTEM = "System"
    ARIAL = "Arial"
    HELVETICA = "Helvetica"
    GEORGIA = "Georgia"
    TIMES = "Times"
    VERDANA = "Verdana"
    COURIER = "Courier"


class FontSettings(ValidatedModel):
    """Font settings for different text types with validation."""

    headline: str = Field(default="System", description="Font for headlines")
    body: str = Field(default="System", description="Font for body text")
    caption: str = Field(default="System", description="Font for captions")

    @field_validator("headline", "body", "caption")
    @classmethod
    def validate_font_options(cls, v):
        """Validate that font values are valid FontOption enum values."""
        valid_fonts = [font.value for font in FontOption]
        if v not in valid_fonts:
            raise ValueError(f"Font must be one of: {', '.join(valid_fonts)}")
        return v


class ReadingSettings(ValidatedModel):
    """Complete reading settings configuration with enum validation."""

    font_size: FontSize = Field(
        default=FontSize.MEDIUM, description="Font size setting"
    )
    fonts: FontSettings = Field(
        default_factory=FontSettings, description="Font family settings"
    )
    font_weight: FontWeight = Field(
        default=FontWeight.NORMAL, description="Font weight setting"
    )
    line_spacing: LineSpacing = Field(
        default=LineSpacing.STANDARD, description="Line spacing setting"
    )
    color_mode: ColorMode = Field(
        default=ColorMode.DEFAULT, description="Color mode setting"
    )


class ReadingSettingsUpdate(ValidatedModel):
    """Reading settings update schema - all fields optional with enum validation."""

    font_size: FontSize | None = Field(None, description="Font size setting")
    fonts: FontSettings | None = Field(None, description="Font family settings")
    font_weight: FontWeight | None = Field(None, description="Font weight setting")
    line_spacing: LineSpacing | None = Field(None, description="Line spacing setting")
    color_mode: ColorMode | None = Field(None, description="Color mode setting")
