from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel


class AuthenticationLog(BaseModel):

    __tablename__ = "authentication_log"
    __table_args__ = {"extend_existing": True}

    id = Column("aulo_cd_id", Integer, primary_key=True)
    logged_at = Column(
        "aulo_dt_logged_at", DateTime, default=datetime.now, nullable=False
    )
    ip_address = Column("aulo_nr_ip_address", String(45), nullable=True)

    auth_id = Column("auth_cd_id", Integer, ForeignKey("authentication.auth_cd_id"))
    auth = relationship("Authentication", uselist=False, lazy="select")
    event_type = Column("aulo_tx_event_type", String(100), nullable=False)
    session_token = Column("aulo_tx_reset_token", String(150), nullable=True)
