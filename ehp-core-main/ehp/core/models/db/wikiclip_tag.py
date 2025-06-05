from sqlalchemy import Column, ForeignKey, Index, Table

from ehp.db import sqlalchemy_async_connector as db


wikiclip_tag = Table(
    "wikiclip_tag",
    db.Base.metadata,
    Column("wiki_cd_id", ForeignKey("wikiclip.wiki_cd_id"), primary_key=True),
    Column("tag_cd_id", ForeignKey("tag.tag_cd_id"), primary_key=True),
    Index("idx_tag_cd_id", "tag_cd_id"),
    Index("idx_wiki_cd_id", "wiki_cd_id"),
    extend_existing=True,
)
