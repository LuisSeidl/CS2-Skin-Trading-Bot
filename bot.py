from pathlib import Path
import json
from helpers.logger import LoggingSystem
from datetime import timedelta
from typing import Optional
from entities import PlatformName
from Clients.dmarket import DMarketClient
from databaseClient import DatabaseClient


KEYS_FILE = Path("keys.json") 

def load_keys(path: Path) -> tuple[str, str, str]:
    with open(path) as f:
        data = json.load(f)
    return data["DMARKET_PUBLIC"], data["DMARKET_PRIVATE"], data["DB_LOCAL"]

# DMarket fetch config
GAME_ID       = "a8db"          # CS2
CURRENCY      = "USD"
LIMIT         = 10            # items per page (DMarket max is 100)
MAX_PAGES     = 1               # set to None to paginate until exhausted


class Bot:
    def __init__(self, limit: int = 100, max_pages: int = 10):
        pub, priv, db = load_keys(KEYS_FILE)
        self.dbClient = DatabaseClient(db)

        LIMIT = limit
        MAX_PAGES = max_pages

        dMarketKeys = {
            "public_key": pub,
            "secret_key": priv
        }
        self.dMarketClient = DMarketClient(dMarketKeys, LIMIT)


    def cleanUp(self, listings_before: timedelta):
        """Recursively deletes all stored listings with a last_seen_at below today - listings_before"""
        self.dbClient.cleanup_listings(listings_before)


    def mainApplication(self):
        results = self.dMarketClient.getData(MAX_PAGES)
        state = self.dbClient.insertResults(results)
        if state == 0:
            LoggingSystem.app.info("===================== Finished Inserting Items =====================")
        self.dbClient.stopFloatRangePopulator()

