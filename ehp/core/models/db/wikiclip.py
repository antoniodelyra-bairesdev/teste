from sqlalchemy import JSON, TIMESTAMP, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ehp.core.models.db.base import BaseModel
from ehp.utils.date_utils import timezone_now

from .wikiclip_tag import wikiclip_tag


class WikiClip(BaseModel):
    __tablename__ = "wikiclip"
    __table_args__ = {"extend_existing": True}

    id = Column("wiki_cd_id", Integer, primary_key=True)
    title = Column("wiki_tx_title", String(500), nullable=False)
    content = Column("wiki_tx_content", Text, nullable=False)
    url = Column("wiki_tx_url", String(2000), nullable=False)
    related_links = Column("wiki_js_related_links", JSON, nullable=True)
    created_at = Column(
        "wiki_dt_created_at",
        TIMESTAMP(timezone=True),
        default=timezone_now,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        "user_cd_id", Integer, ForeignKey("user.user_cd_id"), nullable=True
    )

    tags = relationship(
        "Tag",
        secondary=wikiclip_tag,
        back_populates="wikiclips",
        lazy=False,
        order_by="Tag.description",
    )
    analyses = relationship("Analysis", back_populates="wikiclip")
    user = relationship("User")
