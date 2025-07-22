from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from ehp.core.models.db.base import BaseModel
from ehp.utils.date_utils import timezone_now

from .wikiclip_tag import wikiclip_tag


class WikiClip(BaseModel):
    __tablename__ = "wikiclip"

    id: Mapped[int] = mapped_column("wiki_cd_id", Integer, primary_key=True)
    title: Mapped[str] = mapped_column("wiki_tx_title", String(500), nullable=False)
    summary: Mapped[str] = mapped_column("wiki_tx_summary", Text, nullable=True)
    content: Mapped[str] = mapped_column("wiki_tx_content", Text, nullable=False)
    url: Mapped[str | None] = mapped_column("wiki_tx_url", String(2000), nullable=True)
    related_links: Mapped[dict | list | None] = mapped_column("wiki_js_related_links", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
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
    details = relationship("WikiClipDetail", back_populates="wikiclip")
    user = relationship("User")
