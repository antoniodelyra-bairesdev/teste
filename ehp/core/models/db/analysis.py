from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel


class Analysis(BaseModel):
    __tablename__ = "analysis"
    __table_args__ = {"extend_existing": True}

    id = Column("anls_cd_id", Integer, primary_key=True)
    result = Column("anls_tx_result", Text, nullable=False)
    created_at = Column(
        "wiki_dt_created_at", DateTime, default=datetime.now, nullable=False
    )

    agent_id = Column(
        "agen_cd_id", Integer, ForeignKey("agent.agen_cd_id"), nullable=False
    )
    agent = relationship("Agent", back_populates="analyses", uselist=False)

    wikiclip_id = Column(
        "wiki_cd_id", Integer, ForeignKey("wikiclip.wiki_cd_id"), nullable=False
    )
    wikiclip = relationship("WikiClip", back_populates="analyses", uselist=False)
