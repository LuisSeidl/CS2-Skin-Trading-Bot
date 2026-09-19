import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    PrimaryKeyConstraint,
    ForeignKeyConstraint,
    and_,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlatformName(str, enum.Enum):
    dmarket  = "dmarket"
    skinport = "skinport"
    steam    = "steam"
    csmoney  = "csmoney"
    buff163  = "buff163"
    waxpeer  = "waxpeer"
    empire   = "empire"


class ExteriorType(str, enum.Enum):
    uncalculated   = "uncalculated"
    unspecified    = "unspecified"
    factory_new    = "factory new"
    minimal_wear   = "minimal wear"
    field_tested   = "field-tested"
    well_worn      = "well-worn"
    battle_scarred = "battle-scarred"
    not_painted    = "not painted"


class QualityType(str, enum.Enum):
    unspecified   = "unspecified"
    consumer      = "consumer"
    industrial    = "industrial"
    mil_spec      = "mil_spec"
    restricted    = "restricted"
    classified    = "classified"
    covert        = "covert"
    distinguished = "distinguished"
    exceptional   = "exceptional"
    superior      = "superior"
    master        = "master"
    base_grade    = "base_grade"
    extraordinary = "extraordinary"
    high_grade    = "high_grade"
    remarkable    = "remarkable"
    exotic        = "exotic"
    contraband    = "contraband"
    stock         = "stock"

class WeaponType(str, enum.Enum):
    equipment       = "equipment"
    pistol          = "pistol"
    sniper_rifle    = "sniper rifle"
    rifle           = "rifle"
    smg             = "smg"
    shotgun         = "shotgun"
    knife           = "knife"
    agent           = "agent"
    sticker         = "sticker"
    container       = "container"
    machinegun      = "machinegun"
    graffiti        = "graffiti"
    gloves          = "gloves"
    charm           = "charm"
    
class Marketplace(str, enum.Enum):
    dmarket = "dmarket"

class ListingStatus(str, enum.Enum):
    default = "default"

class OpportunityType(str, enum.Enum):
    snipe     = "snipe"
    arbitrage = "arbitrage"
    trade_up  = "trade_up"


class OpportunityStatus(str, enum.Enum):
    detected = "detected"
    pending  = "pending"
    executed = "executed"
    missed   = "missed"
    expired  = "expired"
    invalid  = "invalid"


class TradeStatus(str, enum.Enum):
    pending_buy  = "pending_buy"
    bought       = "bought"
    pending_sell = "pending_sell"
    sold         = "sold"
    failed_buy   = "failed_buy"
    failed_sell  = "failed_sell"
    cancelled    = "cancelled"

# ---------------------------------------------------------------------------
# Global Dictionaries
# ---------------------------------------------------------------------------

_QUALITY_MAP: dict[str, str] = {
    # Standard grades
    "consumer":         "consumer",
    "consumer grade":   "consumer",
    "industrial":       "industrial",
    "industrial grade": "industrial",
    "mil_spec":         "mil_spec",
    "mil-spec":         "mil_spec",
    "mil-spec grade":   "mil_spec",
    "restricted":       "restricted",
    "classified":       "classified",
    "covert":           "covert",
    "extraordinary":    "extraordinary",
    "contraband":       "contraband",
}


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# BotSetting
# ---------------------------------------------------------------------------
class BotSetting(Base):
    """Key/value store for runtime bot configuration."""

    __tablename__ = "bot_settings"

    key:         Mapped[str]           = mapped_column(Text, primary_key=True)
    value:       Mapped[Any]           = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at:  Mapped[datetime]      = mapped_column(nullable=False, server_default=func.now())

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
class Collection(Base):
    """CS2 weapon collections and cases."""

    __tablename__ = "collections"

    name:       Mapped[str]      = mapped_column(Text, primary_key=True)
    type:       Mapped[str]      = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('case', 'collection', 'souvenir')", name="ck_collections_type"),
    )

    # relationships — must use Mapped[] in SQLAlchemy 2.0
    weapons:           Mapped[list["Weapon"]]         = relationship("Weapon", back_populates="collection")
    trade_up_routes: Mapped[list["TradeUpRoute"]] = relationship("TradeUpRoute", back_populates="collection")

# ---------------------------------------------------------------------------
# FloatRange
# ---------------------------------------------------------------------------
class FloatRange(Base):
    """Contains the standard and custom cs2 float ranges"""

    __tablename__ = "float_ranges"

    name:                   Mapped[str] = mapped_column(Text, primary_key=True)
    factory_new_from:       Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    factory_new_to:         Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    minimal_wear_from:      Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    minimal_wear_to:        Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    field_tested_from:      Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    field_tested_to:        Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    well_worn_from:         Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    well_worn_to:           Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    battle_scarred_from:    Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    battle_scarred_to:      Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    not_painted:            Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    weapons:      Mapped[Optional[list["Weapon"]]]    = relationship("Weapon", back_populates="float_range")

    def compareRange(self, other: "FloatRange") -> bool:
        return (
            self.factory_new_from == other.factory_new_from and
            self.factory_new_to == other.factory_new_to and
            self.minimal_wear_from == other.minimal_wear_from and
            self.minimal_wear_to == other.minimal_wear_to and
            self.field_tested_from == other.field_tested_from and
            self.field_tested_to == other.field_tested_to and
            self.well_worn_from == other.well_worn_from and
            self.well_worn_to == other.well_worn_to and
            self.battle_scarred_from == other.battle_scarred_from and
            self.battle_scarred_to == other.battle_scarred_to and
            self.not_painted == other.not_painted
        )

    def isFalse(self) -> bool:
        return (
            self.factory_new_from == None and
            self.factory_new_to == None and
            self.minimal_wear_from == None and
            self.minimal_wear_to == None and
            self.field_tested_from == None and
            self.field_tested_to == None and
            self.well_worn_from == None and
            self.well_worn_to == None and
            self.battle_scarred_from == None and
            self.battle_scarred_to == None and
            self.not_painted == False
        )
        
    def findExteriorType(self, floatValue: float) -> ExteriorType:
        result = ExteriorType.not_painted

        if floatValue < self.factory_new_to:
            result = ExteriorType.factory_new
        if floatValue < self.minimal_wear_to:
            result = ExteriorType.minimal_wear
        if floatValue < self.field_tested_to:
            result = ExteriorType.field_tested
        if floatValue < self.well_worn_to:
            result = ExteriorType.well_worn
        if floatValue <= self.battle_scarred_to:
            result = ExteriorType.battle_scarred

        return result
    
# ---------------------------------------------------------------------------
# Weapon
# ---------------------------------------------------------------------------
class Weapon(Base):
    __tablename__ = "weapons"

    full_name:      Mapped[str] = mapped_column(Text, primary_key=True)
    name:           Mapped[str] = mapped_column(Text, nullable=False)
    skin:           Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    weapon_type:    Mapped[str] = mapped_column(Text, nullable=False)
    quality:        Mapped[str] = mapped_column(Text, nullable=False)
    collection_name:  Mapped[Optional[str]] = mapped_column(ForeignKey("collections.name"))
    float_range_name: Mapped[Optional[str]] = mapped_column(ForeignKey("float_ranges.name"))


    # back_populates verweist auf "weapons" in der Collection-Klasse
    collection:     Mapped[Optional["Collection"]] = relationship("Collection", back_populates="weapons")
    float_range:    Mapped[Optional["FloatRange"]] = relationship("FloatRange", back_populates="weapons")
    items:          Mapped[list["Item"]]           = relationship("Item", back_populates="weapon")

# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------
class Item(Base):
    """One row per unique skin variant (name + exterior + stattrak/souvenir)."""

    __tablename__ = "items"

    weapon_full_name:      Mapped[Optional[str]] = mapped_column(ForeignKey("weapons.full_name"))
    float_value:   Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    exterior_type:  Mapped[Optional[str]] = mapped_column(String(20))
    is_stattrak: Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    is_souvenir: Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    paint_index: Mapped[Optional[int]]     = mapped_column(Integer)

    steam_class_id:     Mapped[Optional[str]] = mapped_column(Text)
    marketplace: Mapped[Optional[str]] = mapped_column(Text)
    marketplace_id: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now(),
                                                  onupdate=func.now())

    __table_args__ = (
        Index("idx_items_steam_class", "steam_class_id"),
        PrimaryKeyConstraint("marketplace", "marketplace_id")
    )
    

    weapon:          Mapped[Optional["Weapon"]]        = relationship("Weapon",        back_populates="items")
    listings:        Mapped[list["Listing"]]           = relationship("Listing",       back_populates="item", primaryjoin="and_(Item.marketplace == Listing.marketplace, Item.marketplace_id == Listing.marketplace_item_id)",cascade= "all, delete")
    price_snapshots: Mapped[list["PriceSnapshot"]]     = relationship("PriceSnapshot", back_populates="item", primaryjoin="and_(Item.marketplace == PriceSnapshot.marketplace, Item.marketplace_id == PriceSnapshot.marketplace_item_id)",cascade= "all, delete")
    price_stats:     Mapped[list["PriceStat"]]         = relationship("PriceStat",     back_populates="item", primaryjoin="and_(Item.marketplace == PriceStat.marketplace, Item.marketplace_id == PriceStat.marketplace_item_id)",cascade= "all, delete")
    trades:          Mapped[list["Trade"]]             = relationship("Trade",          back_populates="item", primaryjoin="and_(Item.marketplace == Trade.marketplace, Item.marketplace_id == Trade.marketplace_item_id)",cascade= "all, delete")

# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
class Listing(Base):
    """Active market offer from any platform."""

    __tablename__ = "listings"

    id:       Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True,
                                                     server_default=func.gen_random_uuid())
    offer_id: Mapped[str]           = mapped_column(Text, nullable=False)
    marketplace:        Mapped[str]                = mapped_column(Text, nullable=False)
    marketplace_item_id: Mapped[Optional[str]]     = mapped_column(Text)
    price_cents:           Mapped[int]           = mapped_column(Integer, nullable=False)
    tradable:           Mapped[bool]               = mapped_column(Boolean, nullable=False, default=True)
    trade_lock_until:   Mapped[Optional[datetime]] = mapped_column()
    trade_lock_seconds: Mapped[Optional[int]]      = mapped_column(Integer)
    stickers:                  Mapped[Optional[Any]] = mapped_column(JSONB)
    owner_id:     Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str]  = mapped_column(Text, nullable=False, default="active")
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at:    Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    last_seen_at:  Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("marketplace", "offer_id", name="uq_listings_platform_offer"),
        ForeignKeyConstraint(
            ["marketplace", "marketplace_item_id"],
            ["items.marketplace", "items.marketplace_id"],
            name="fk_listings_items_composite"
        ),
        Index("idx_listings_item_platform", "marketplace_item_id", "marketplace",
              postgresql_where=text("status = 'active'")),
        Index("idx_listings_price",     "price_cents",
              postgresql_where=text("status = 'active'")),
        Index("idx_listings_fetched_at","fetched_at",
              postgresql_ops={"fetched_at": "DESC"}),
        Index("idx_listings_trade_lock","trade_lock_until",
              postgresql_where=text("tradable = FALSE")),
    )

    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="listings", foreign_keys="[Listing.marketplace, Listing.marketplace_item_id]")
# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------
class Opportunity(Base):
    """Detected trading opportunity (snipe, arbitrage, or trade-up).

    detail JSONB schemas by type:
    - snipe:     { listing_id, item_id, platform, ref_price_cents, discount_pct,
                   sticker_value_cents, float_value }
    - arbitrage: { listing_id, buy_platform, sell_platform,
                   buy_price_cents, sell_price_cents,
                   buy_fee_cents, sell_fee_cents }
    - trade_up:  { input_listing_ids[], route_id, expected_output_item_id,
                   output_probabilities: [{item_id, probability, ev_cents}],
                   avg_normalized_float,      # Oct-2025 per-skin normalization
                   expected_output_float,
                   expected_ev_cents }
    """

    __tablename__ = "opportunities"

    id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                               server_default=func.gen_random_uuid())
    type:   Mapped[str]       = mapped_column(String(20), nullable=False)
    status: Mapped[str]       = mapped_column(String(20), nullable=False,
                                               default=OpportunityStatus.detected.value)
    estimated_cost_cents:    Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_revenue_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_profit_cents:  Mapped[int] = mapped_column(
                                              Integer,
                                              Computed(
                                                  "estimated_revenue_cents - estimated_cost_cents",
                                                  persisted=True,),)
    profit_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4))
    detail: Mapped[Any] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime]           = mapped_column(nullable=False, server_default=func.now())
    expires_at:  Mapped[Optional[datetime]] = mapped_column()
    executed_at: Mapped[Optional[datetime]] = mapped_column()
    created_at:  Mapped[datetime]           = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_opp_type_status", "type", "status"),
        Index("idx_opp_profit", "estimated_profit_cents",
              postgresql_ops={"estimated_profit_cents": "DESC"},
              postgresql_where=text("status = 'detected'")),
        Index("idx_opp_detected_at", "detected_at",
              postgresql_ops={"detected_at": "DESC"}),
    )

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="opportunity", cascade="all, delete")

# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------
class Platform(Base):
    """Per-platform fee structure and API config."""

    __tablename__ = "platforms"

    id:                 Mapped[str]           = mapped_column(String(20), primary_key=True)
    display_name:       Mapped[str]           = mapped_column(Text, nullable=False)
    buy_fee_pct:        Mapped[Decimal]       = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))
    sell_fee_pct:       Mapped[Decimal]       = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))
    withdrawal_fee_pct: Mapped[Decimal]       = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))
    min_fee_cents:      Mapped[int]           = mapped_column(Integer, nullable=False, default=0)
    api_base_url:       Mapped[Optional[str]] = mapped_column(Text)
    active:             Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    updated_at:         Mapped[datetime]      = mapped_column(nullable=False, server_default=func.now())

# ---------------------------------------------------------------------------
# PriceSnapshot
# ---------------------------------------------------------------------------
class PriceSnapshot(Base):
    """Raw price events. Consider TimescaleDB hypertable if volume is high."""

    __tablename__ = "price_snapshots"

    id:          Mapped[int]               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    marketplace:         Mapped[str]               = mapped_column(Text, nullable=False)
    marketplace_item_id: Mapped[Optional[str]]     = mapped_column(Text)
    price_cents: Mapped[int]               = mapped_column(Integer, nullable=False)
    float_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 9))
    recorded_at: Mapped[datetime]          = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_price_snapshots_lookup", "marketplace", "marketplace_item_id", "recorded_at",
              postgresql_ops={"recorded_at": "DESC"}),
        ForeignKeyConstraint(
            ["marketplace", "marketplace_item_id"],
            ["items.marketplace", "items.marketplace_id"],
            name="fk_price_snapshots_items_composite"
        ),
    )

    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="price_snapshots", foreign_keys="[PriceSnapshot.marketplace, PriceSnapshot.marketplace_item_id]")
# ---------------------------------------------------------------------------
# PriceStat
# ---------------------------------------------------------------------------
class PriceStat(Base):
    """Pre-computed price aggregates, refreshed by a background job."""

    __tablename__ = "price_stats"
    id:          Mapped[int]               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    marketplace:         Mapped[str]           = mapped_column(Text, nullable=False)
    marketplace_item_id: Mapped[Optional[str]] = mapped_column(Text)
    period:   Mapped[str] = mapped_column(Text, primary_key=True)  # d1 | d3 | d7 | d30

    min_cents:    Mapped[Optional[int]] = mapped_column(Integer)
    max_cents:    Mapped[Optional[int]] = mapped_column(Integer)
    avg_cents:    Mapped[Optional[int]] = mapped_column(Integer)
    median_cents: Mapped[Optional[int]] = mapped_column(Integer)
    p10_cents:    Mapped[Optional[int]] = mapped_column(Integer)
    volume:       Mapped[Optional[int]] = mapped_column(Integer)

    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("period IN ('d1', 'd3', 'd7', 'd30')", name="ck_price_stats_period"),
        ForeignKeyConstraint(
            ["marketplace", "marketplace_item_id"],
            ["items.marketplace", "items.marketplace_id"],
            name="fk_price_stats_items_composite"
        ),
    )

    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="price_stats", foreign_keys="[PriceStat.marketplace, PriceStat.marketplace_item_id]")
# ---------------------------------------------------------------------------
# StickerCatalog
# ---------------------------------------------------------------------------
class StickerCatalog(Base):
    """Sticker catalog — used to estimate sticker value contribution on listings."""

    __tablename__ = "sticker_catalog"

    id:                    Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:                  Mapped[str]           = mapped_column(Text, nullable=False, unique=True)
    image_url:             Mapped[Optional[str]] = mapped_column(Text)
    estimated_value_cents: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at:            Mapped[datetime]      = mapped_column(nullable=False, server_default=func.now())

# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------
class Trade(Base):
    """Execution record for a single buy/sell or trade-up leg."""

    __tablename__ = "trades"

    id:             Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True,
                                                                server_default=func.gen_random_uuid())
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opportunities.id"))
    type:           Mapped[str]                = mapped_column(String(20), nullable=False)

    buy_platform:  Mapped[Optional[str]] = mapped_column(String(20))
    sell_platform: Mapped[Optional[str]] = mapped_column(String(20))
    marketplace:        Mapped[str]                = mapped_column(Text, nullable=False)
    marketplace_item_id: Mapped[Optional[str]]     = mapped_column(Text)

    buy_price_cents:  Mapped[Optional[int]] = mapped_column(Integer)
    sell_price_cents: Mapped[Optional[int]] = mapped_column(Integer)
    buy_fee_cents:    Mapped[Optional[int]] = mapped_column(Integer)
    sell_fee_cents:   Mapped[Optional[int]] = mapped_column(Integer)
    net_profit_cents: Mapped[Optional[int]] = mapped_column(Integer)

    status:        Mapped[str]           = mapped_column(String(20), nullable=False,
                                                          default=TradeStatus.pending_buy.value)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    parent_trade_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("trades.id"))

    # "metadata" is a reserved attribute name in SQLAlchemy — use metadata_ mapped to "metadata" column
    metadata_: Mapped[Optional[Any]] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now(),
                                                  onupdate=func.now())

    __table_args__ = (
        Index("idx_trades_opportunity", "opportunity_id"),
        Index("idx_trades_status",      "status"),
        Index("idx_trades_parent",      "parent_trade_id",
              postgresql_where=text("parent_trade_id IS NOT NULL")),
        ForeignKeyConstraint(
            ["marketplace", "marketplace_item_id"],
            ["items.marketplace", "items.marketplace_id"],
            name="fk_trades_items_composite"
        ),
    )

    opportunity: Mapped[Optional["Opportunity"]] = relationship("Opportunity", back_populates="trades", cascade="all, delete")
    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="trades", foreign_keys="[Trade.marketplace, Trade.marketplace_item_id]")

    child_trades: Mapped[list["Trade"]]   = relationship(
        "Trade",
        foreign_keys=[parent_trade_id],
        back_populates="parent_trade",
    )
    parent_trade: Mapped[Optional["Trade"]] = relationship(
        "Trade",
        foreign_keys=[parent_trade_id],
        back_populates="child_trades",
        remote_side="Trade.id",
    )

# ---------------------------------------------------------------------------
# TradeUpRoute
# ---------------------------------------------------------------------------
class TradeUpRoute(Base):
    """Pre-calculated trade-up routes per quality + collection.

    Float Output Formula (October 2025 update — enforce in application layer):
    --------------------------------------------------------------------------
    For each of the N input skins (N=10 non-Covert, N=5 Covert):
        normalized_i = (input_float_i - items.float_min_i) / (items.float_max_i - items.float_min_i)
    avg_normalized = SUM(normalized_i) / N
    output_float   = output_float_min + avg_normalized * (output_float_max - output_float_min)

    Each input skin's float_min/float_max MUST be fetched individually from the
    items table — do NOT share one range across all inputs.

    possible_outputs JSONB schema:
        [{item_id, name, weight}]
        weight / 10 = probability of that output skin.
    """

    __tablename__ = "trade_up_routes"

    id:             Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_name:  Mapped[str] = mapped_column(ForeignKey("collections.name"), nullable=False)
    input_quality:  Mapped[str] = mapped_column(String(20), nullable=False)
    output_quality: Mapped[str] = mapped_column(String(20), nullable=False)
    possible_outputs: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at:     Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("collection_name", "input_quality",
                         name="uq_trade_up_routes_collection_quality"),
    )

    collection: Mapped[Optional["Collection"]] = relationship("Collection", back_populates="trade_up_routes")



class StandardizedResult:
    weapon: Weapon
    item: Item
    listing: Listing

    def __init__(self, weapon: Weapon, item: Item, listing: Listing) -> None:
        self.weapon = weapon
        self.item = item
        self.listing = listing

    def getweapon(self) -> Weapon:
        return self.weapon

    def getItem(self) -> Item:
        return self.item

    def getListing(self) -> Listing:
        return self.listing