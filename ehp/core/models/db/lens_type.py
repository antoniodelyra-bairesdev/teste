from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ehp.core.models.db.base import BaseModel


class LensType(BaseModel):
    __tablename__ = "lens_type"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column("lens_tp_cd_id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("lens_tp_tx_name", String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(
        "lens_tp_tx_description", String(500), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "lens_tp_dt_created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    if TYPE_CHECKING:
        from ehp.core.models.db.lens import Lens

        lenses: Mapped[list[Lens]]
