from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel


class User(BaseModel):

    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    id = Column("user_cd_id", Integer, primary_key=True)
    full_name = Column("user_tx_full_name", String(250), nullable=False)
    created_at = Column(
        "user_dt_created_at", DateTime, default=datetime.now, nullable=False
    )

    auth_id = Column("auth_cd_id", Integer, ForeignKey("authentication.auth_cd_id"))
    authentication = relationship(
        "Authentication", uselist=False, back_populates="user", lazy=False
    )

    country_id = Column(
        "coun_cd_id", Integer, ForeignKey("country.coun_cd_id"), nullable=True
    )
    country = relationship("Country", uselist=False)
