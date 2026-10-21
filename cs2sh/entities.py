from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, PrimaryKeyConstraint, DateTime, Numeric, Index, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    metadata = MetaData(schema="cs2sh")

class TmpCollection(Base):
    __tablename__= "tmp_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    released: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    update_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    collection_item_maps: Mapped[list["TmpCollectionItemMap"]]  = relationship("TmpCollectionItemMap", back_populates="tmp_collection", lazy="selectin")
    

class TmpRarity(Base):
    __tablename__= "tmp_rarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tier: Mapped[int] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(10))

    tmp_items: Mapped[list["TmpItem"]] = relationship("TmpItem", back_populates="rarity", lazy="selectin")


class TmpCollectionItemMap(Base):
    __tablename__="tmp_collection_item_map"

    item_name: Mapped[Optional[str]] = mapped_column(ForeignKey("tmp_items.market_hash_name"))
    collection_name: Mapped[str] = mapped_column(ForeignKey("tmp_collections.name"))
    tmp_item: Mapped["TmpItem"]      = relationship("TmpItem", back_populates="collection_maps")
    tmp_collection: Mapped["TmpCollection"]  = relationship("TmpCollection", back_populates="collection_item_maps")

    __table_args__ = (
        PrimaryKeyConstraint("item_name", "collection_name"),
    )

class TmpContainerItemMap(Base):
    __tablename__="tmp_container_item_map"

    item_name: Mapped[str] = mapped_column(ForeignKey("tmp_items.market_hash_name"))
    container_name: Mapped[str] = mapped_column(String(256), nullable=False)
    tmp_item: Mapped["TmpItem"]      = relationship("TmpItem", back_populates="container_maps")

    __table_args__ = (
        PrimaryKeyConstraint("item_name", "container_name"),
    )


class TmpItem(Base):
    __tablename__= "tmp_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_hash_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    image: Mapped[str] = mapped_column(String(512), nullable = True)
    tradable: Mapped[bool] = mapped_column(Boolean)
    rarity_name: Mapped[str] = mapped_column(ForeignKey("tmp_rarities.name"))

    weapon_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    finish_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    wear: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    wear_min: Mapped[Optional[float]] = mapped_column(Numeric(5,4), nullable=True)
    wear_max: Mapped[Optional[float]] = mapped_column(Numeric(5,4), nullable=True)
    has_stattrak: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    has_souvenir: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    buff_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    youpin_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    c5game_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


    rarity: Mapped["TmpRarity"]  = relationship("TmpRarity", back_populates="tmp_items", lazy="selectin")
    collection_maps: Mapped[list["TmpCollectionItemMap"]] = relationship("TmpCollectionItemMap", back_populates="tmp_item", lazy="selectin")
    container_maps: Mapped[list["TmpContainerItemMap"]] = relationship("TmpContainerItemMap", back_populates="tmp_item", lazy="selectin")
    prices: Mapped[list["TmpItemPrice"]] = relationship("TmpItemPrice", back_populates="tmp_item", lazy="selectin")


class TmpItemPrice(Base):
    __tablename__= "tmp_items_prices"

    collected_at_time: Mapped[DateTime] = mapped_column(DateTime)
    updated_at_time: Mapped[DateTime] = mapped_column(DateTime)

    item_id: Mapped[int] = mapped_column(ForeignKey("tmp_items.id"), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    ask: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    ask_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bid: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    bid_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tmp_item: Mapped["TmpItem"] = relationship("TmpItem", back_populates="prices")

    __table_args__ = (
        PrimaryKeyConstraint(collected_at_time, item_id, platform),
        Index("idx_item_platform_pricing", "item_id", "collected_at_time", "platform"),
    )