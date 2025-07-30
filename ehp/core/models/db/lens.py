# pyright: reportImportCycles=false
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ehp.core.models.db.base import BaseModel
from ehp.utils.date_utils import timezone_now


class Lens(BaseModel):
    __tablename__ = "lens"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column("lens_cd_id", Integer, primary_key=True)
    title: Mapped[str] = mapped_column("lens_tx_title", String(250), nullable=False)
    content: Mapped[str] = mapped_column("lens_tx_content", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "lens_dt_created_at",
        TIMESTAMP(timezone=True),
        default=timezone_now,
        nullable=False,
    )
    lens_type_id: Mapped[int] = mapped_column(
        "lens_tp_cd_id", Integer, ForeignKey("lens_type.lens_tp_cd_id"), nullable=False
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        "lens_dt_disabled_at", TIMESTAMP(timezone=True), nullable=True
    )

    lens_type = relationship("LensType", back_populates="lenses")

    if TYPE_CHECKING:
        from ehp.core.models.db.lens_type import LensType

        lens_type: Mapped[LensType]
