from typing import Optional
import helpers.utils as utils
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select, and_, update, delete, func
from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from helpers.logger import LoggingSystem
from entities import Base, Weapon, Collection, FloatRange, Item, Listing, StandardizedResult
from helpers.populateFloatRange import FloatRangePopulator

class DatabaseClient:

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.floatRangePopulator = FloatRangePopulator()

    def stopFloatRangePopulator(self):
        self.floatRangePopulator.__shutdown__()

    def __return_pk(self, instance):
        if type(instance) == Weapon:
            return instance.full_name
        elif type(instance) == Item:
            return instance.id
        elif type(instance) == Listing:
            return instance.id

    def cleanup_listings(self, window: timedelta) -> None:
        session = self.session
        try:
            stmt = delete(Listing).where(Listing.last_seen_at < (datetime.now() - window))
            result = session.execute(stmt)
            session.commit()
            LoggingSystem.cleanup.info(f"Cleaned up {result.rowcount} Listings")
        except Exception as e:
            session.rollback()
            raise e

    def cleanup_items(self, window: timedelta)-> None:
        session = self.session
        try:
            stmt = delete(Item).where(Item.updated_at < (datetime.now() - window))
            result = session.execute(stmt)
            session.commit()
            LoggingSystem.cleanup.info(f"Cleaned up {result.rowcount} Items")
        except Exception as e:
            session.rollback()
            raise e
        
    def merge_instance(self, instance):
        session = self.session
        try:
            session.merge(instance)
            session.commit()
            return self.__return_pk(instance)
        except Exception as e:
            session.rollback()
            raise e

    def insert_instances(self, instances: list):
        session = self.session
        try:
            session.add_all(instances)
            session.commit()
        except Exception as e:
            LoggingSystem.app.error("Inserting Instaces threw an exception: " + e)
            session.rollback()
        finally:
            session.close()

    def insert_one_by_one(self, instances: list):
        session = self.session()
        try:
            for instance in instances:
                session.add(instance)
                session.commit()
        except Exception as e:
            session.rollback()
            LoggingSystem.app.warning(f"Error occured for instance: {instance}")
            raise e
        finally:
            session.close()

    def merge_instances(self, instances: list):
        """Inserts or updates the given fixtures in the database
        Uses SQLAlchemy merge(), which will insert if not found, or update if exists, based on the primary key"""

        with self.session() as session:
            try:
                for instance in instances:
                    session.merge(instance)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
            finally:
                LoggingSystem.app.info(f"Finished updating instances: {instance}")

    def merge_one_by_one(self, instances: list):
        """Inserts or updates the given instances in the database """

        with self.session() as session:
            try:
                for instance in instances:
                    session.merge(instance)
                    session.commit()
            except Exception as e:
                session.rollback()
                raise e
            finally:
                LoggingSystem.app.info(f"Finished updating instances: {instance}")


    def __ensure_collection(self, name: str) -> str:
        """Get or create a Collection row; return the name (pk)"""
        row = self.session.scalar(select(Collection).where(Collection.name == name))
        if row:
            return row.name
        new = Collection(name = name, type="collection")
        self.session.add(new)
        self.session.flush()
        LoggingSystem.app.info("Created new collection: %s", name)
        return name

    def __ensure_float_range(self, item: FloatRange) -> str:
        """Get or create a float range row; return the name(pk)"""
        row = self.session.scalar(select(FloatRange).where(FloatRange.compareRange(FloatRange,item)))
        if row:
            return row.name
        self.session.add(item)
        self.session.flush()
        LoggingSystem.app.info("Created new float range: %s", item.name)
        return item.name
    
    def __get_ExteriorType(self, weaponName: str, floatValue: float) -> Optional[str]:
        """Based on the weapon and float value gets the corresponding exterior type"""
        weapon_res = self.session.scalar(select(Weapon).where(Weapon.full_name == weaponName))
        if weapon_res is None:
            LoggingSystem.app.warning(f"No weapon {weaponName} exists in Weapon Table")
            return None

        float_range = self.session.scalar(select(FloatRange).where(Weapon.float_range_name == weapon_res.float_range_name))

        if float_range is None:
            LoggingSystem.app.warning(f"No float range {float_range} for weapon {weaponName} exists in FloatRange Table")
            return None
        
        ext_type = float_range.findExteriorType(floatValue)

        return ext_type.name 


    def insert_item(self, attributes: dict, cs2: dict) -> Optional[int]:
        """Inserts an item from DMarket, merges if it exists already"""

        # 1. check if the underlying weapon exists and create if not
        weapon_val = self.__ensure_weapon(attributes, cs2)
        if not weapon_val:
            LoggingSystem.app.warning(f"Failed to find weapon: {weapon_val}")

        # Parse classId — DMarket format "8529624800:8246937075"
        class_id_full: str = attributes.get("classId", "")
        steam_class_id = class_id_full.split(":")[0] if ":" in class_id_full else class_id_full

        is_stattrak = "stattrak" in attributes.get("title", "").lower()
        is_souvenir = "souvenir" in attributes.get("title", "").lower()

        float_val = cs2.get("float")
        ext_type = self.__get_ExteriorType(weapon_val, float_val)

        instance = Item(
            weapon_full_name = weapon_val,
            float_value = float_val,
            exterior_type = ext_type,
            is_stattrak = is_stattrak,
            is_souvenir = is_souvenir,
            paint_index = cs2.get("paintIndex"),
            steam_class_id   = steam_class_id,
            dmarket_product_id = attributes.get("productId"),
            image_url        = attributes.get("imageUri"),
            name_color       = attributes.get("nameColor"),
        )

        return self.merge_instance(instance)

    def insert_listing(self, raw: dict, attributes: dict, cs2: dict, item_id: int, platform: str) -> Optional[int]:
        offer_id = raw.get("offerId")
        price_cents     = utils._parse_usd_cents(raw.get("priceCents"))

        trade_lock_secs: Optional[int] = attributes.get("tradeLockDuration")
        settlement_raw: Optional[str]  = attributes.get("settlementTime")
        trade_lock_until: Optional[datetime] = None
        if settlement_raw:
            try:
                trade_lock_until = datetime.fromisoformat(settlement_raw.replace("Z", "+00:00"))
            except ValueError:
                pass

        stickers_raw  = cs2.get("stickers") or []
        stickers_data = utils._parse_sticker_slots(stickers_raw) if stickers_raw else None

        instance = Listing(
            offer_id                  = offer_id,
            platform                  = platform,
            item_id                   = item_id,
            price_cents               = price_cents,
            suggested_price_cents     = 0,
            tradable                  = attributes.get("tradable", True),
            trade_lock_until          = trade_lock_until,
            trade_lock_seconds        = trade_lock_secs,
            stickers                  = stickers_data,
            owner_id                  = attributes.get("owner"),
            owner_wallet              = attributes.get("steamAssetId"),
            status                    = attributes.get("status", "active"),
            is_new                    = attributes.get("isNew", False),
            fetched_at                = datetime.now(timezone.utc),
            first_seen_at             = datetime.now(timezone.utc),
            last_seen_at              = datetime.now(timezone.utc),
        )

        return self.merge_instance(instance)
    


    def ingest_items(self, items: list[dict], platform: str) -> tuple[int, int]:
        """
        Parse and upsert a batch of raw DMarket listing dicts.
        Returns (inserted_or_updated_items, skipped).
        """
        ok = skipped = 0
        for raw in items:
            attributes = raw.get("attributes") or {}
            cs2 = attributes.get("cs2") or {}
            try:
                item_id = self.insert_item(attributes, cs2)
                self.insert_listing(raw, attributes,cs2, item_id, platform)
                ok += 1
            except Exception as exc:
                LoggingSystem.app.warning("Failed to ingest item %s: %s", attributes.get("id"), exc)
                skipped += 1
        return ok, skipped


    def __ensure_weapon(self, weapon: Weapon) -> Optional[str]:
        """Makes sure that the data needed for the weapon exist and merges the weapon"""
        if weapon.collection_name:
            weapon.collection_name = self.__ensure_collection(weapon.collection_name)

        float_range = self.floatRangePopulator.get_float_range(weapon.full_name)
        if float_range:
             weapon.float_range_name = self.__ensure_float_range(float_range)

        return self.merge_instance(weapon)

    def insert_item(self, item: Item) -> Optional[int]:
        """Inserts an item from DMarket, merges if it exists already"""

        # 1. check if the underlying weapon exists and create if not
        weapon_val = self.__ensure_weapon(attributes, cs2)
        if not weapon_val:
            LoggingSystem.app.warning(f"Failed to find weapon: {weapon_val}")

        # Parse classId — DMarket format "8529624800:8246937075"
        class_id_full: str = attributes.get("classId", "")
        steam_class_id = class_id_full.split(":")[0] if ":" in class_id_full else class_id_full

        is_stattrak = "stattrak" in attributes.get("title", "").lower()
        is_souvenir = "souvenir" in attributes.get("title", "").lower()

        float_val = cs2.get("float")
        ext_type = self.__get_ExteriorType(weapon_val, float_val)

        instance = Item(
            weapon_full_name = weapon_val,
            float_value = float_val,
            exterior_type = ext_type,
            is_stattrak = is_stattrak,
            is_souvenir = is_souvenir,
            paint_index = cs2.get("paintIndex"),
            steam_class_id   = steam_class_id,
            dmarket_product_id = attributes.get("productId"),
            image_url        = attributes.get("imageUri"),
            name_color       = attributes.get("nameColor"),
        )

        return self.merge_instance(instance)


    def insertResult(self, result: StandardizedResult):
        weapon_val = self.__ensure_weapon(result.weapon)
        if not weapon_val:
            LoggingSystem.app.warning(f"Failed to find weapon: {weapon_val}")

        result.item.exterior_type = self.__get_ExteriorType(weapon_val, result.item.float_value)