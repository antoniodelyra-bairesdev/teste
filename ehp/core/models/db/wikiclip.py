from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel
from .wikiclip_tag import wikiclip_tag


class WikiClip(BaseModel):
    __tablename__ = "wikiclip"
    __table_args__ = {"extend_existing": True}

    id = Column("wiki_cd_id", Integer, primary_key=True)
    title = Column("wiki_tx_title", String(250), nullable=False)
    content = Column("wiki_tx_content", Text, nullable=False)
    url = Column("wiki_tx_url", String(250), nullable=False)
    created_at = Column(
        "wiki_dt_created_at", DateTime, default=datetime.now, nullable=False
    )

    tags = relationship(
        "Tag",
        secondary=wikiclip_tag,
        back_populates="wikiclips",
        lazy=False,
        order_by="Tag.description",
    )

    analyses = relationship("Analysis", back_populates="wikiclip")
