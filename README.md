# CS2-Skin-Trading-Bot
Trying to implement a bot that automatically buys/sells CS2 skins based on common financial concepts

## Algorithms

### Main Algorithm

Runs every x seconds, has high priority

1. Fetch Market Data every x seconds (prob every 5 minutes, as thats min limit for most Clients) -> only dmarket for now
2. Based on Data, calculate possible tradeup routes, their costs and compare expected value with the value of current existing items listings
    -> Add to opportunites if one found

### Cleanup Algorithm

Runs every hour, has lower priority than Main Algorithm

Recursively deletes all entries from the listings table, which have 'last seen at' < 1 week ago