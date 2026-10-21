from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from cs2sh.entities import Base, TmpItem


class DataBaseClient:
    def __init__(self, db_url: str):
            self.engine = create_engine(db_url)
            Base.metadata.create_all(self.engine)
            self.session = Session(self.engine)

    def merge(self, instances: list):
        with self.session as session:
            for instance in instances:
                try: 
                    session.merge(instance)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Rollback for item {instance} of type {type(instance)}, exception: {e}")
                    continue

    def bulkInsertPrice(self, model, instances: list[dict]) -> int:
        """
            Uses Bulk-insert to quickly insert all price instances
            Parameter list has to contain all instances of the model object type. else it fails
            Returns
            0 on Success
            1 on Exception
        """
        if not instances:
            return 0
        
        with self.session as session:
            try:
                stmt = pg_insert(model)
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements= ["collected_at_time", "item_id", "platform"],
                    set_= {
                        "updated_at_time": stmt.excluded.updated_at_time,
                        "ask": stmt.excluded.ask,
                        "ask_volume": stmt.excluded.ask_volume,
                        "bid": stmt.excluded.bid,
                        "bid_volume": stmt.excluded.bid_volume,
                    }
                )

                session.execute(upsert_stmt, instances)
                session.commit()
                return 0
            except Exception as e:
                session.rollback()
                print(f"Rollback for {model.__tablename__}, exception: {e}")
                return 1

    def bulkInsertDoNothing(self, model, instances: list[dict]) -> int:
        """
            Uses Bulk-insert to quickly insert all item instances
            On Duplicate it does nothing
            Parameter list has to contain all instances of the model object type. else it fails
            Returns
            0 on Success
            1 on Exception
        """
        if not instances:
            return 0
        
        with self.session as session:
            try:
                stmt = pg_insert(model)
                upsert_stmt = stmt.on_conflict_do_nothing()

                session.execute(upsert_stmt, instances)
                session.commit()
                return 0
            except Exception as e:
                session.rollback()
                print(f"Rollback for {model.__tablename__}, exception: {e}")
                return 1

    def item_name_to_id_dict(self) -> dict:
        """
        Returns a dict containing { "market_hash_name" : id} for all items
        """
        item_name_id_dict = dict()

        with self.session as session:
            item_name_id_dict = {
                name : idx for idx, name in session.execute(select(TmpItem.id, TmpItem.market_hash_name))
            }

        return item_name_id_dict
