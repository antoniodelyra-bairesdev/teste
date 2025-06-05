from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel


class Authentication(BaseModel):

    __tablename__ = "authentication"
    __table_args__ = ({"extend_existing": True})

    id = Column("auth_cd_id", Integer, primary_key=True)
    user_name = Column("auth_tx_name", String(150), nullable=False)
    user_email = Column("auth_tx_email", String(300), nullable=False)
    user_pwd = Column("auth_tx_pwd", String(150), nullable=False)

    created_at = Column(
        "auth_dt_created_at",
        DateTime,
        default=datetime.now(),
        nullable=False
    )
    is_active = Column("auth_st_active", String(1), default="1", nullable=False)
    is_confirmed = Column(
        "auth_st_confirmed", String(1), default="0", nullable=False
    )
    confirmation = Column("auth_dt_confirmation", DateTime)
    accept_terms = Column(
        "auth_st_accept_terms", String(1), default="0", nullable=False
    )
    reset_password = Column(
        "auth_st_reset_password", String(1), default="0", nullable=False
    )
    user = relationship(
        "User", uselist=False, back_populates="authentication", lazy=False
    )

    profile_id = Column(
        "prof_cd_id", Integer, ForeignKey("profile.prof_cd_id")
    )
    profile = relationship(
        "Profile",
        uselist=False,
        lazy=False
    )
