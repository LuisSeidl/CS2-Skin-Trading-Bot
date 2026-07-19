from pathlib import Path
import json
from helpers.logger import LoggingSystem
from datetime import timedelta
from typing import Optional
from entities import PlatformName
from Clients.dmarket import DMarketClient
from databaseClient import DatabaseClient


KEYS_FILE = Path("keys.json") 

with open(KEYS_FILE) as f:
    data = json.load(f)
    DB_URL = data["DATABASE"]

def load_keys(path: Path) -> tuple[str, str]:
    with open(path) as f:
        data = json.load(f)
    return data["DMARKET_PUBLIC"], data["DMARKET_PRIVATE"], data["DATABASE"]

# DMarket fetch config
GAME_ID       = "a8db"          # CS2
CURRENCY      = "USD"
LIMIT         = 10            # items per page (DMarket max is 100)
MAX_PAGES     = 10               # set to None to paginate until exhausted
PLATFORM_ID   = PlatformName.dmarket


class Bot:
    def __init__(self):
        pub, priv, db = load_keys(KEYS_FILE)
        self.dbClient = DatabaseClient(db)
        self.dMarketClient = DMarketClient(pub, priv)


    def cleanUp(self, listings_before: timedelta):
        """Recursively deletes all stored listings with a last_seen_at below today - listings_before"""
        self.dbClient.cleanup_listings(listings_before)


    def mainApplication(self):
        cursor: Optional[str] = None
        total_ok = total_skipped = 0
        page = 0

        while True:
            page += 1
            LoggingSystem.app.info("Fetching page %d (cursor=%s)…", page, cursor or "start")

            items, cursor = self.dMarketClient.fetch_market_page(cursor=cursor, limit=LIMIT)
            if not items:
                LoggingSystem.app.info("No items returned — done.")
                break
            
            ok, skipped = self.dbClient.ingest_items(items, PLATFORM_ID.value )
            total_ok      += ok
            total_skipped += skipped
            LoggingSystem.app.info("Page %d: %d upserted, %d skipped.", page, ok, skipped)
            
            if not cursor:
                LoggingSystem.app.info("No more pages.")
                break
            if MAX_PAGES and page >= MAX_PAGES:
                LoggingSystem.app.info("Reached MAX_PAGES=%d — stopping.", MAX_PAGES)
                break

        LoggingSystem.app.info(
            "Ingest complete: %d total upserted, %d total skipped.",
            total_ok, total_skipped,
        )

        self.dbClient.stopFloatRangePopulator()

