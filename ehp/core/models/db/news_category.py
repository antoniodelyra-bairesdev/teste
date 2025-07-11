from sqlalchemy import Column, Integer, String

from ehp.core.models.db.base import BaseModel


class NewsCategory(BaseModel):
    __tablename__ = "news_category"
    __table_args__ = {"extend_existing": True}

    id = Column("ncat_cd_id", Integer, primary_key=True)
    name = Column("ncat_tx_name", String(150), nullable=False)
