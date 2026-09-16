from Clients.dmarket import DMarketClient
import json

with open("keys.json") as f:
    keys = json.load(f)

dmarketKeys = {
    "public_key": keys["DMARKET_PUBLIC"],
    "secret_key": keys["DMARKET_PRIVATE"]
}

client = DMarketClient(dmarketKeys, 10)

client.test_authorization()