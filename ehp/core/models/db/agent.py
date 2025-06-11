from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel


class Agent(BaseModel):
    __tablename__ = "agent"
    __table_args__ = {"extend_existing": True}

    id = Column("agen_cd_id", Integer, primary_key=True)
    name = Column("agen_tx_name", String(250), nullable=False)
    prompt = Column("agen_tx_prompt", Text, nullable=False)
    created_at = Column(
        "wiki_dt_created_at", DateTime, default=datetime.now, nullable=False
    )
    analyses = relationship(
        "Analysis",
        back_populates="agent",
    )
