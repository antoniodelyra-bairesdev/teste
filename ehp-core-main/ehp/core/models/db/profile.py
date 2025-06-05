from sqlalchemy import Column, Integer, String

from ehp.core.models.db.base import BaseModel


class Profile(BaseModel):
    __tablename__ = "profile"
    __table_args__ = {"extend_existing": True}

    id = Column("prof_cd_id", Integer, primary_key=True)
    name = Column("prof_tx_name", String(45), nullable=False)
    code = Column("prof_cd_code", String(10), nullable=False)
