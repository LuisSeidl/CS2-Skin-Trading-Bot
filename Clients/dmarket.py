import json 
from datetime import datetime
import requests
from typing import Optional
from urllib.parse import quote, urlencode
from nacl.bindings import crypto_sign
from entities import Weapon, Item, Listing, StandardizedResult

# DMarket fetch config
GAME_ID       = "a8db"          # CS2
LIMIT = 10
CURRENCY      = "USD"

class DMarketClient:
    _ROOT = "https://api.dmarket.com"
    _PREFIX = "dmar ed25519 "

    def __init__(self, public_key: str, secret_key: str) -> None:
        if not public_key or not secret_key:
            raise ValueError("Public and secret keys must be provided.")
        self._public_key = public_key
        self._secret_key = secret_key

    def call(self, method: str, path: str, payload: dict | None = None):
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
            "X-Api-Key": self._public_key,
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
        signed = crypto_sign(s.encode(), bytes.fromhex(self._secret_key))
        return signed[:64].hex()


    def fetch_market_page(
        self,
        cursor: Optional[str] = None,
        limit: int = LIMIT,
    ) -> tuple[list[dict], Optional[str]]:
        """
        Fetch one page of market items from DMarket.
        Returns (items_list, next_cursor).
        """
        params: dict = {
            "gameId":   GAME_ID,
            "limit":    limit,
            "currency": CURRENCY,
        }
        if cursor:
            params["cursor"] = cursor

        data, error = self.call("GET", "/marketplace-api/v2/offers", payload=params)
        if error:
            raise RuntimeError(f"DMarket API error: {error}")

        items  = data.get("items") or []
        cursor = data.get("cursor")        # None / "" means no more pages
        return items, cursor or None



    def buildWeapon(self, attributes: dict, cs2: dict) -> Weapon:
        full_name_val = attributes.get("name")
        quality_val = cs2.get("quality")

        # Collection will be ensured in databaseClient
        collection_raw = cs2.get("collection") or []
        if collection_raw:
            collection_name = collection_raw[0].strip() if collection_raw[0] else None

        #Float range will be ensured in databaseClient
        float_range_name = "NO_FLOAT_RANGE"

        return Weapon(
            full_name= full_name_val,
            name = str(full_name_val).split("|")[0],
            skin = str(full_name_val).split("|")[1],
            weapon_type = cs2.get("itemType", "unknown"),
            quality = quality_val,
            category_path = attributes.get("categoryPath"),
            collection_name = collection_name,
            float_range_name = float_range_name
        )

    def buildItem(self, attributes: dict, cs2: dict) -> Item:


    def standardizeData(self, attributes: dict, cs2: dict) -> list[StandardizedResult]:

        #1. 

    