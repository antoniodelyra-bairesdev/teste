from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from ehp.core.models.db.base import BaseModel
from .wikiclip_tag import wikiclip_tag


class Tag(BaseModel):
    __tablename__ = "tag"
    __table_args__ = {"extend_existing": True}

    id = Column("tag_cd_id", Integer, primary_key=True)
    description = Column("tag_tx_description", String(150), nullable=False)

    wikiclips = relationship(
        "WikiClip",
        secondary=wikiclip_tag,
        back_populates="tags",
        lazy=False,
        order_by="WikiClip.title",
    )
