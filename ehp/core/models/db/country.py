from sqlalchemy import Column, Integer, String

from ehp.core.models.db.base import BaseModel


class Country(BaseModel):
    __tablename__ = "country"
    __table_args__ = {"extend_existing": True}

    id = Column("coun_cd_id", Integer, primary_key=True)
    name = Column("coun_tx_name", String(150), nullable=False)
    code = Column("coun_cd_code", String(5), nullable=False)
