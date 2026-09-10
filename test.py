# import requests
# import json
# from helpers.utils import dumpToTempFile
# from Clients.dmarket import DMarketClient

# with open("keys.json", "r") as f:
#     data = json.load(f)
#     DB_URL = data["DB_LOCAL"]
#     PUB = data["DMARKET_PUBLIC"]
#     PRIV = data["DMARKET_PRIVATE"]


# client = DMarketClient(public_key=PUB, secret_key=PRIV)

# result = client.fetch_market_page(limit = 10)
# result
# dumpToTempFile(result)

import enum

from entities import WeaponType

teststring = "pistol"

print(type(WeaponType(teststring).value))