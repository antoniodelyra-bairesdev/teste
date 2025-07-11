from datetime import datetime
from typing import TYPE_CHECKING

from ehp.utils.constants import (
    AUTH_ACCEPT_TERMS,
    AUTH_ACTIVE,
    AUTH_CONFIRMED,
    AUTH_RESET_PASSWORD,
)
from ehp.core.models.db.base import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Authentication(BaseModel):
    __tablename__ = "authentication"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column("auth_cd_id", Integer, primary_key=True)
    user_name: Mapped[str] = mapped_column("auth_tx_name", String(150), nullable=False)
    user_email: Mapped[str] = mapped_column("auth_tx_email", String(300), nullable=False)
    user_pwd: Mapped[str] = mapped_column("auth_tx_pwd", String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        "auth_dt_created_at", DateTime, default=datetime.now, nullable=False
    )
    is_active: Mapped[str] = mapped_column(
        "auth_st_active", String(1), default=AUTH_ACTIVE, nullable=False
    )
    is_confirmed: Mapped[str] = mapped_column(
        "auth_st_confirmed", String(1), default=AUTH_CONFIRMED, nullable=False
    )
    confirmation: Mapped[datetime] = mapped_column(
        "auth_dt_confirmation", DateTime, nullable=True
    )
    accept_terms: Mapped[str] = mapped_column(
        "auth_st_accept_terms", String(1), default=AUTH_ACCEPT_TERMS, nullable=False
    )
    reset_password: Mapped[str] = mapped_column(
        "auth_st_reset_password", String(1), default=AUTH_RESET_PASSWORD, nullable=False
    )
    reset_token: Mapped[str | None] = mapped_column(
        "auth_tx_reset_token", String(255), nullable=True
    )
    reset_token_expires: Mapped[datetime | None] = mapped_column(
        "auth_dt_reset_token_expires", DateTime, nullable=True
    )

    # Email change fields
    pending_email: Mapped[str | None] = mapped_column(
        "auth_tx_pending_email", String(300), nullable=True
    )
    email_change_token: Mapped[str | None] = mapped_column(
        "auth_tx_email_change_token", String(255), nullable=True
    )
    email_change_token_expires: Mapped[datetime | None] = mapped_column(
        "auth_dt_email_change_token_expires", DateTime, nullable=True
    )

    user = relationship(
        "User", uselist=False, back_populates="authentication", lazy=False
    )

    profile_id: Mapped[int] = mapped_column(
        "prof_cd_id", Integer, ForeignKey("profile.prof_cd_id"), nullable=True
    )
    profile = relationship("Profile", uselist=False, lazy=False)

    retry_count: Mapped[int] = mapped_column(
        "auth_nr_retry_count", Integer, default=0, nullable=False
    )
    last_login_attempt: Mapped[datetime] = mapped_column(
        "auth_dt_last_login_attempt", DateTime, default=datetime.now, nullable=False
    )

    if TYPE_CHECKING:
        from ehp.core.models.db.profile import Profile
        from ehp.core.models.db.user import User

        user: Mapped[User]
        profile: Mapped[Profile]
