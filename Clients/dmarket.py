import json 
from datetime import datetime
import requests
from typing import Optional
from urllib.parse import quote, urlencode
from nacl.bindings import crypto_sign
from entities import Weapon, Item, Listing, StandardizedResult, WeaponType, QualityType, ExteriorType, Marketplace, ListingStatus
from clientInterface import ClientInterface
from helpers.logger import LoggingSystem
from helpers.utils import _parse_quality, _parse_exterior

#Mapping for converting API enums to our enum
_DMARKET_QUALITY_MAP: dict[str, str] = {
    # Standard grades
    "QUALITY_UNSPECIFIED":      "unspecified",
    "QUALITY_CONSUMER_GRADE":   "consumer",
    "QUALITY_INDUSTRIAL_GRADE": "industrial",
    "QUALITY_MIL_SPEC":         "mil_spec",
    "QUALITY_RESTRICTED":       "restricted",
    "QUALITY_CLASSIFIED":       "classified",
    "QUALITY_COVERT":           "covert",
    "QUALITY_DISTINGUISHED":    "distinguished",
    "QUALITY_EXCEPTIONAL":      "exceptional",
    "QUALITY_SUPERIOR":         "superior",
    "QUALITY_MASTER":           "master",
    "QUALITY_BASE_GRADE":       "base_grade",
    "QUALITY_EXTRAORDINARY":    "extraordinary",
    "QUALITY_HIGH_GRADE":       "high_grade",
    "QUALITY_REMARKABLE":       "remarkable",
    "QUALITY_EXOTIC":           "exotic",
    "QUALITY_CONTRABAND":       "contraband",
    "QUALITY_STOCK":            "stock",
}

_DMARKET_EXTERIOR_MAP: dict[str, str] = {
    "EXTERIOR_UNSPECIFIED":     "unspecified",
    "EXTERIOR_FACTORY_NEW":     "factory_new",
    "EXTERIOR_MINIMAL_WEAR":    "minimal_wear",
    "EXTERIOR_FIELD_TESTED":    "field_tested",
    "EXTERIOR_WELL_WORN":       "well_worn",
    "EXTERIOR_BATTLE_SCARRED":  "battle_scarred",
    "EXTERIOR_NOT_PAINTED":     "not_painted",

}

class DMarketClient(ClientInterface):
    _ROOT = "https://api.dmarket.com"
    _PREFIX = "dmar ed25519 "
    _GAME_ID = "a8db"
    _CURRENCY = "USD"

    keys = dict()
    limit = 0

    def __init__(self, keys: dict , limit: int) -> None:
        if not keys["public_key"] or not keys["secret_key"]:
            raise ValueError("Public and secret keys must be provided.")
        self.keys = keys
        self.limit = limit

    def __call(self, method: str, path: str, payload: dict | None = None):
        method = method.upper()
        nonce = str(round(datetime.now().timestamp()))
        api_path = path
        body = ""

        if payload:
            if method == "GET":
                api_path = f"{path}?{urlencode(payload, quote_via=quote)}"
            else:
                body = json.dumps(payload)

        sig = self._sign(method + api_path + body + nonce)
        headers = {
            "X-Api-Key": self.keys["public_key"],
            "X-Request-Sign": self._PREFIX + sig,
            "X-Sign-Date": nonce,
        }
        if method != "GET" and payload:
            headers["Content-Type"] = "application/json"

        try:
            r = requests.request(
                method,
                self._ROOT + api_path,
                headers=headers,
                data=body.encode() if body else None,
                timeout=15,
            )
            r.raise_for_status()
            return r.json(), None
        except requests.RequestException as e:
            detail = e.response.text if e.response else "no body"
            return None, f"{e} — {detail}"

    def _sign(self, s: str) -> str:
        signed = crypto_sign(s.encode(), bytes.fromhex(self.keys["secret_key"]))
        return signed[:64].hex()
    
    def __fetchMarketPage(self, cursor: str | None = None) -> tuple[list[dict], str | None]:
        """
        Fetch one page of market items from DMarket.
        Returns (items_list, next_cursor).
        """
        params: dict = {
            "gameId":   self._GAME_ID,
            "limit":    self.limit,
            "currency": self._CURRENCY,
        }
        if cursor:
            params["cursor"] = cursor

        data, error = self.__call("GET", "/marketplace-api/v2/offers", payload=params)
        if error:
            raise RuntimeError(f"DMarket API error: {error}")

        items  = data.get("items") or []
        cursor = data.get("cursor")        # None / "" means no more pages
        return items, cursor or None

        
    def __standardizeResult(self, content: dict | list) -> list[StandardizedResult]:
        items = content[0]
        result = []

        for item in items:
            attributes = item.get("attributes")
            cs2 = attributes.get("cs2")

            # 1. Build Weapon
            full_name_val = attributes.get("name")
            quality_raw = cs2.get("quality")

            if quality_raw:
                quality_raw = _DMARKET_QUALITY_MAP.get(quality_raw)
                quality = _parse_quality(quality_raw)

            # Collection will be ensured in databaseClient
            collection_raw = cs2.get("collection") or []
            if collection_raw:
                collection_name = collection_raw[0].strip() if collection_raw[0] else None

            #Float range will be ensured in databaseClient
            float_range_name = "NO_FLOAT_RANGE"

            weapon_type_raw = cs2.get("itemType", "unknown")
            if weapon_type_raw:
                weapon_type = WeaponType(weapon_type_raw).value

            weapon = Weapon(
                full_name= full_name_val,
                name = str(full_name_val).split("|")[0],
                skin = str(full_name_val).split("|")[1],
                weapon_type = weapon_type,
                quality = quality,
                category_path = attributes.get("categoryPath"),
                collection_name = collection_name,
                float_range_name = float_range_name
            )

            # 2. build item
            class_id_full: str = attributes.get("classId", "")
            steam_class_id = class_id_full.split(":")[0] if ":" in class_id_full else class_id_full

            exterior_raw = cs2.get("exterior")
            if exterior_raw:
                exterior_raw = _DMARKET_EXTERIOR_MAP.get(exterior_raw)
                exterior = _parse_exterior(exterior_raw)

            item = Item(
                weapon_full_name = full_name_val,
                float_value = cs2.get("float"),
                exterior_type = exterior,
                is_stattrak = cs2.get("category") == "CATEGORY_STATTRACK",
                is_souvenir = cs2.get("category") == "CATEGORY_SOUVENIR",
                paint_index = cs2.get("paintIndex"),
                steam_class_id = steam_class_id,
                marketplace = Marketplace.dmarket,
                marketplace_id = attributes.get("id")
            )

            # 3. build listing
            listing = Listing(
                offer_id = item.get("offerId"),
                marketplace = Marketplace.dmarket.value,
                item_id = None,
                #TODO: item_id has to be updated in databaseClient based on the id that the 
                # item gets
                price_cents = item.get("priceCents"),
                tradeable = attributes.get("tradable") == "true",
                trade_lock_until = attributes.get("unlockDate"),
                trade_lock_seconds = attributes.get("tradeLockDuration"),
                stickers = cs2.get("stickers"),
                owner_id = attributes.get("owner"),
                status = ListingStatus(attributes.get("status")),
                is_new = True,
            )

            result.append(StandardizedResult(weapon, item, listing))

        return result 

    def getData(self, max_pages: int | None = None) -> list[StandardizedResult]:
        cursor: Optional[str] = None
        total_ok = total_skipped = 0
        standardizedResults = []
        page = 0

        while True:
            page += 1
            LoggingSystem.app.info("DMarketClient: Fetching page %d (cursor=%s)...", page, cursor or "start")
            items, cursor = self.__fetchMarketPage(cursor=cursor)
            if not items :
                LoggingSystem.app.info(
                    "DMarketClient finished fetching Data,%d total upserted, %d total skipped.",
                    total_ok, total_skipped, 
                )
                return standardizedResults

            new_items = len(items)
            standardized_items = self.__standardizeResult(items)
            ok = len(standardized_items)
            skipped = new_items-ok

            standardizedResults.extend(standardized_items)

            LoggingSystem.app.info("DMarketClient Page %d: %d upserted, %d skipped",page, ok ,skipped  )
            total_ok += ok
            total_skipped += skipped

            if not cursor or (max_pages and page >= max_pages):
                LoggingSystem.app.info(
                    "DMarketClient finished fetching Data,%d total upserted, %d total skipped.",
                    total_ok, total_skipped, 
                )                
                return standardizedResults
    