#TODO: once use https://cs2.sh/docs/schema and https://cs2.sh/resources/how-to-get-cs2-float-ranges
# to build a database of all existing collections, float ranges, ...
# then once that is saved (make sure to have backup!!)
# for testing rebuild the bot to only save listings / items but to always use already existing items / float ranges
# -> then build a database of listings and prototype

#################################################################################
# STEP 1 Use https://cs2.sh/docs/schema 
# Download all available data from cs2.sh from this endpoint (and look throgh all) in the two day demo phase 
# Then use this data for the bot
from pathlib import Path
import requests
import json
import time
from dateutil.parser import isoparse
from cs2sh.entities import TmpCollection, TmpCollectionItemMap, TmpContainerItemMap, TmpRarity, TmpItem, TmpItemPrice
from cs2sh.dbclient import DataBaseClient

def getData(call_name: str, file_name: str):
    headers = {
        "Authorization": "Bearer demo_vtRVTVRpPswYwQPKNIzMBTgSlGsHMQFz",
        "Accept-Encoding": "gzip",
    }

    response = requests.get(
        call_name,
        headers=headers,
    )

    response.raise_for_status()
    data = response.json()

    with open(f"{file_name}.json", "x") as f:
        json.dump(data,f, indent=4)

def unserialize_collections(data: dict)-> tuple[type, list]:
    collections = []
    for key, value in data.items():
        update_name = released = None

        try:
            if value["update_name"]:
                update_name = value["update_name"]
        except KeyError:
            pass

        try:
            if value["release_date"]:
                released = value["release_date"]
        except KeyError:
            pass

        collections.append({
            "name": value["name"],
            "released": released,
            "update_name": update_name,
            "image": value["image"],
        })
    return (TmpCollection, collections)

def unserialize_items(data: dict) -> list[tuple[type, list]]:
    items = []
    rarities = []
    collection_map = []
    container_map= []
    rarities_seen = set()

    rarities.append({
        "name" : "None",
        "tier" : 0,
        "color" : "#000000"
    })

    for key, value in data.items():

        rarity_name = "None"
        try:
            rarity = value.get("rarity")
            rarity_name = rarity.get("name")
            if rarity_name not in rarities_seen:
                rarities.append({
                    "name": rarity_name,
                    "tier": rarity.get("tier"),
                    "color": rarity.get("color")
                })
                rarities_seen.add(rarity_name)
        except (KeyError, AttributeError):
            pass

        try:
            id = value["ids"]
            buff_id = id.get("buff")
            youpin_id = id.get("youpin")
            c5game_id = id.get("c5game")
        except KeyError:
            pass

        market_hash_name = value.get("market_hash_name")
        item_category= value.get("category")

        wear_min = wear_max = None
        try:
            float_range = value.get("wear_float_range")
            wear_min = float(float_range.get("min"))
            wear_max = float(float_range.get("max"))
        except (KeyError, AttributeError):
            pass

        items.append({
            "market_hash_name": market_hash_name,
            "category": item_category,
            "image":  value.get("steam_image"),
            "tradable": bool(value.get("is_tradable")),
            "rarity_name": str(rarity_name),

            "weapon_name": value.get("weapon", None),
            "finish_name": value.get("finish", None),
            "wear": value.get("wear", None),
            "wear_min": wear_min,
            "wear_max": wear_max,

            "has_stattrak": bool(value.get("has_stattrak")),
            "has_souvenir": bool(value.get("has_souvenir")),

            "buff_id": str(buff_id) if buff_id else None,
            "youpin_id": str(youpin_id) if youpin_id else None,
            "c5game_id": str(c5game_id) if c5game_id else None,
        }
        )

        try: 
            collections = value.get("collections", [])
            for col in collections:
                collection_map.append({
                    "item_name": market_hash_name,
                    "collection_name": col,
                })

        except (KeyError, AttributeError):
            pass

        try:
            containers = value.get("containers", [])
            for con in containers:
                container_map.append({
                    "item_name": market_hash_name, 
                    "container_name": con, 
                })
        except (KeyError, AttributeError):
            pass
 
    return  [(TmpRarity, rarities), (TmpItem, items), (TmpCollectionItemMap, collection_map), (TmpContainerItemMap,container_map)]

def unserialize_schema() -> list[tuple[type, list]]:
    with open("cs2sh/schema.json") as f:
        data = json.load(f)
        collections = unserialize_collections(data["collections"])
        item_data  = unserialize_items(data["items"])
        item_data.append(collections)
        return item_data
        

        
def unserialize_prices(data: dict,item_name_to_id_dict: dict ) -> list[dict]:
    tmp_item_prices = []
    for item_name, platforms in data.items():

        item_id = item_name_to_id_dict.get(item_name)
        if not item_id:
            continue

        for platform_name, platform_data in platforms.items():
            if platform_name == "market_hash_name":
                continue

            collected_at_raw = platform_data.get("collected_at")
            updated_at_raw = platform_data.get("updated_at")

            if not collected_at_raw or not updated_at_raw:
                continue
            
            tmp_item_prices.append({
                "collected_at_time": isoparse(collected_at_raw),
                "updated_at_time": isoparse(updated_at_raw),
                "item_id": item_id,
                "platform": platform_name,
                "ask": platform_data.get("ask"),
                "ask_volume": platform_data.get("ask_volume"),
                "bid": platform_data.get("bid"),
                "bid_volume": platform_data.get("bid_volume")
            })

    return tmp_item_prices

def get_prices(item_name_to_id_dict: dict) -> list[dict]:
    with open("cs2sh/prices_latest.json") as f:
        data = json.load(f)
        return unserialize_prices(data["items"], item_name_to_id_dict)



KEYS_FILE = Path("keys.json") 

def load_keys(path: Path) -> str:
    with open(path) as f:
        data = json.load(f)
    return data["DB_LOCAL"]

dbclient = DataBaseClient(load_keys(KEYS_FILE))


item_data = unserialize_schema()

for tup in item_data:
    model = tup[0]
    lst = tup[1]
    print("#"*20)
    start = time.time()
    dbclient.bulkInsertDoNothing(model,lst)
    end = time.time()
    print(f"Finished Upserting {type(model)} | Number of Entries: {len(lst)}| Elapsed Time: {end-start} Seconds")

print("")
print("#"*20)
print("Finished Getting Items")

#getData("https://api.cs2.sh/v1/market/steam/latest", "cs2sh/steam_latest")

print("Starting to Get Data from Dict")
start = time.time()
item_name_id_dict = dbclient.item_name_to_id_dict()
tmp_item_prices = get_prices(item_name_id_dict)
print("#"*20)
end = time.time()
print(f"Finished to Get Data from Dict | Elapsed Time: {end-start} Seconds")

print("#"*20)
print(f"Starting upsert prices into DB")
start = time.time()
response = dbclient.bulkInsertPrice(TmpItemPrice, tmp_item_prices)
print("#"*20)
end = time.time()
print(f"Finished upserting prices into DB | Elapsed Time: {end-start} Seconds")
