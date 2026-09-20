from typing import Optional
import helpers.utils as utils
from datetime import datetime, timezone, timedelta
from sqlalchemy import UUID, create_engine, select, and_, update, delete, func, inspect
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

    def test(self):
        inspector = inspect(self.engine)
        schemas = inspector.get_schema_names()

        for schema in schemas:
            print("Schema %s" % schema)
            for table_name in inspector.get_table_names(schema=schema):
                print("Table %s" % table_name)

    def stopFloatRangePopulator(self):
        self.floatRangePopulator.__shutdown__()

    def __return_pk(self, instance):
        _type = type(instance)
        if _type == Weapon:
            return instance.full_name
        elif _type == Item:
            return (instance.marketplace, instance.marketplace_id)
        elif _type == Listing:
            return (instance.marketplace, instance.offer_id)
        elif _type == Collection:
            return instance.name
        else: 
            return -1

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

    def __merge(self, instance):
        """
        Inserts or updates the given instance in the database
        Uses SQLAlchemy merge(), which will insert if not found, or update if exists, based on the primary key
        """
        with self.session as session:
            try:
                session.merge(instance)
                session.commit()
            except Exception as e:
                session.rollback()
                LoggingSystem.app.exception(f"Rollback for item {instance} of type {type(instance)}, exception: {e}")
                raise e
            finally:
                return self.__return_pk(instance)

            
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

    def __getExteriorType(self, weaponName: str, floatValue: float) -> Optional[str]:
        """Based on the weapon and float value gets the corresponding exterior type"""
        weapon_res = self.session.scalar(select(Weapon).where(Weapon.full_name == weaponName))
        if weapon_res is None:
            LoggingSystem.app.warning(f"No weapon {weaponName} exists in Weapon Table")
            return None

        float_range = self.session.scalar(select(FloatRange).join(Weapon.float_range))

        if float_range is None:
            LoggingSystem.app.warning(f"No float range {float_range} for weapon {weaponName} exists in FloatRange Table")
            return None
        
        ext_type = float_range.findExteriorType(floatValue)

        return ext_type.name 

    ##################################################################################
    ######################## NEW FUNCTIONS ###########################################
    ##################################################################################

    def __insertWeapon(self, weapon: Weapon):
        """
        Makes sure that the data needed for the weapon exist and merges the weapon
        Checks if the weapon already exists 
         -> skips creating the float_range and collection if true 
         -> else create both entries first, then merge
        """
        row = self.session.scalar(select(Weapon).where(Weapon.full_name == weapon.full_name))
        if row:
            return row.full_name
        
        if weapon.collection_name:
            weapon.collection_name = self.__ensure_collection(weapon.collection_name)

        float_range = self.floatRangePopulator.get_float_range(weapon.full_name)
        if float_range:
             weapon.float_range_name = self.__ensure_float_range(float_range)
        return self.__merge(weapon)


    def __insertItem(self, item: Item):
        """Inserts Item, merges on item attributes"""
        return self.__merge(item)

    def __insertListing(self, listing: Listing):
        """Inserts a specific listing, merges based on offerId"""
        return self.__merge(listing)

    
    def insertResult(self, result: StandardizedResult) -> int:
        """
        Inserts one StandardizedResult based on Weapon, Item, Listing
        Returns 1 on error and 0 on success 
        """
        weaponPk = self.__insertWeapon(result.weapon)
        if type(weaponPk) is not str:
            LoggingSystem.app.warning(f"Failed to insert weapon: {weaponPk}")
            return 1

        if result.item.exterior_type is None and result.item.float_value is not None:
            result.item.exterior_type = self.__getExteriorType(weaponPk, float(result.item.float_value))
            result.item.weapon_full_name = weaponPk

        itemPk = self.__insertItem(result.item)

        if type(itemPk) is not tuple or len(itemPk) < 2:
            LoggingSystem.app.warning(f"Failed to insert item Marketplace {result.item.marketplace} | ID: {result.item.marketplace_id}")
            return 1
        
        result.listing.marketplace_item_id = itemPk[1]
        listingPk = self.__insertListing(result.listing)

        if type(listingPk) is not tuple or len(listingPk) < 2:
            LoggingSystem.app.warning(f"Failed to insert listing Marketplace {result.listing.marketplace} | Offer_ID: {result.listing.offer_id}")
            return 1

        return 0

    def insertResults(self, results: list[StandardizedResult])-> int:
        state = 0

        while state == 0:
            for res in results:
                state = self.insertResult(res)
        return state