from pathlib import Path
import json
import logging 
from typing import Optional
from entities import PlatformName
from Clients.dmarket import DMarketClient
from databaseClient import DatabaseClient
# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

KEYS_FILE = Path("keys.json")   # same path as your existing code

with open(KEYS_FILE) as f:
    data = json.load(f)
    DB_URL = data["DATABASE"]

# DMarket fetch config
GAME_ID       = "a8db"          # CS2
CURRENCY      = "USD"
LIMIT         = 10            # items per page (DMarket max is 100)
MAX_PAGES     = 10               # set to None to paginate until exhausted
PLATFORM_ID   = PlatformName.dmarket

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_keys(path: Path) -> tuple[str, str]:
    with open(path) as f:
        data = json.load(f)
    return data["DMARKET_PUBLIC"], data["DMARKET_PRIVATE"], data["DATABASE"]


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    pub, priv, db = load_keys(KEYS_FILE)

    dbClient = DatabaseClient(db)

    dMarketClient = DMarketClient(public_key=pub, secret_key=priv)

    cursor: Optional[str] = None
    total_ok = total_skipped = 0
    page = 0

    while True:
        page += 1
        log.info("Fetching page %d (cursor=%s)…", page, cursor or "start")

        items, cursor = dMarketClient.fetch_market_page(cursor=cursor, limit=LIMIT)
        if not items:
            log.info("No items returned — done.")
            break
        
        ok, skipped = dbClient.ingest_items(items, PLATFORM_ID.value )
        total_ok      += ok
        total_skipped += skipped
        log.info("Page %d: %d upserted, %d skipped.", page, ok, skipped)
        
        if not cursor:
            log.info("No more pages.")
            break
        if MAX_PAGES and page >= MAX_PAGES:
            log.info("Reached MAX_PAGES=%d — stopping.", MAX_PAGES)
            break

    log.info(
        "Ingest complete: %d total upserted, %d total skipped.",
        total_ok, total_skipped,
    )

    dbClient.__shutdown__()

if __name__ == "__main__":
    main()