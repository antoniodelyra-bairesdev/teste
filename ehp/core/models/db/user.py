from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.base import BaseModel
from ehp.core.models.db.country import Country
from ehp.utils.constants import DISPLAY_NAME_MAX_LENGTH
from ehp.utils.date_utils import timezone_now


class User(BaseModel):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column("user_cd_id", Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(
        "user_tx_full_name", String(250), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(
        "user_tx_display_name",
        String(DISPLAY_NAME_MAX_LENGTH),
        unique=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "user_dt_created_at",
        DateTime(timezone=True),
        default=timezone_now,
        nullable=False,
    )
    last_update: Mapped[datetime | None] = mapped_column(
        "user_dt_last_update",
        DateTime(timezone=True),
        nullable=True,
    )
    readability_preferences: Mapped[dict[str, Any] | None] = mapped_column(
        "user_js_readability_preferences", JSON, nullable=True
    )
    email_notifications: Mapped[bool] = mapped_column(
        "user_bl_email_notifications", Boolean, default=True, nullable=False
    )
    reading_settings: Mapped[dict[str, Any] | None] = mapped_column(
        "user_js_reading_settings",
        JSON,
        nullable=True,
        default={
            "font_size": "Medium",
            "fonts": {"headline": "System", "body": "System", "caption": "System"},
            "font_weight": "Normal",
            "line_spacing": "Standard",
            "color_mode": "Default",
        },
    )

    avatar: Mapped[str | None] = mapped_column("user_tx_avatar", String(500), nullable=True)

    auth_id: Mapped[int | None] = mapped_column(
        "auth_cd_id", Integer, ForeignKey("authentication.auth_cd_id"), nullable=True
    )
    authentication: Mapped["Authentication | None"] = relationship(
        "Authentication", uselist=False, back_populates="user", lazy=False
    )

    country_id: Mapped[int | None] = mapped_column(
        "coun_cd_id", Integer, ForeignKey("country.coun_cd_id"), nullable=True
    )
    country: Mapped["Country | None"] = relationship("Country", uselist=False)

    preferred_news_categories: Mapped[Any | None] = mapped_column(
        "user_js_preferred_news_categories", JSON, nullable=True
    )

    onboarding_complete: Mapped[bool] = mapped_column(
        "user_bl_onboarding_complete", Boolean, default=False, nullable=False
    )
