from enum import Enum
from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from ehp.core.models.db.base import BaseModel
from ehp.utils.date_utils import timezone_now


class WikiClipDetailType(Enum):
    CONTENT = "content"
    METADATA = "metadata"
    ENRICHMENT = "enrichment"


class WikiClipDetail(BaseModel):
    __tablename__ = "wikiclip_detail"

    id: Mapped[int] = mapped_column("wiki_detail_cd_id", Integer, primary_key=True)
    description: Mapped[str] = mapped_column("wiki_detail_tx_description", Text, nullable=True)
    type: Mapped[str] = mapped_column("wiki_detail_tx_type", String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        "wiki_detail_dt_updated_at",
        TIMESTAMP(timezone=True),
        default=timezone_now,
        onupdate=timezone_now,
        nullable=False,
    )
    wikiclip_id: Mapped[int] = mapped_column(
        "wiki_cd_id", Integer, ForeignKey("wikiclip.wiki_cd_id"), nullable=False
    )
    
    wikiclip = relationship("WikiClip", back_populates="details")
