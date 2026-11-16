# CS2-Skin-Trading-Bot
Trying to implement a bot that automatically buys/sells CS2 skins based on common financial concepts

## Strategy

Using steamdataapi

Forward rolling: 
- every 60s get https://steamdataapi.com/api/v1/items/all?game=cs2&markets=1&variants=1&currency=USD with ETag -> returns all items with prices & quantity for all markets; if n change in the sheet, it returns 304 NOT modified
- every 5 mins get https://steamdataapi.com/api/v1/buy-orders?game=cs2&limit=500&currency=USD

TODO: find a clean way to store it and only change updates to have little data & fast querying

-> implement: 

Phase prices. Dopplers share one marketHashName on Steam, but each phase trades very differently - variants carries the phase-aware prices from the marketplaces that expose the phase per listing. variants appears only on rows that have phases (~1,500 Doppler/Gamma knives of the ~30k catalog); rows without phases are byte-identical with or without variants=1.
Coverage baseline (marketCoverage). With ?markets=1 the response carries a top-level marketCoverage object - per marketplace, how many rows this response embeds and their newest capturedAt. rows is exact: it counts the same rows you'll find in the markets arrays below it - same game filter, same outlier filter - so sum(items.markets where market=X) always equals marketCoverage[X].rows. Use it as a completeness check, not just staleness: a marketplace mid-refresh (DMarket paginates for several minutes; the others land in one batch) or mid-outage can be fresh yet partial, and comparing rows against your previous pull catches that where capturedAt alone cannot.

Coverage. Seven marketplaces publish bids: CSFloat, Buff163, YouPin, C5Game, DMarket, Market.CSGO and Steam. Bids refresh on the same 5–10 minute sync cadence as asks (Steam's about once a day per item): a bid the market withdraws leaves with its next complete refresh (one that looks broken — a feed suddenly missing most of its book — is held back for up to an hour first), and if a market stops answering, or answers only in part, its bids stop being served after 3 hours (Steam: 36 hours) rather than ageing silently. A market's bid above that same market's lowest ask is never served: a standing order there would fill at once unless it only buys certain copies (a float range, a pattern, a phase) or the feed is wrong — either way it isn't what the plain item sells into. Steam's bid is listed but never best: it pays in Steam Wallet funds, which can't be withdrawn, and routinely tops every cash marketplace's ask — counting it would show a fake arbitrage on most liquid items. Ask for it alone with market=steam (then best is Steam's bid). spread is only given between the same kind of money: it is null when the bid and the ask are not both Steam or both cash — for instance when the cheapest ask is Steam's own.


demand. demand is the total number of items wanted across that item's entire book on that market, where the market publishes it: CSFloat (every price level, phase- and float-targeted orders included; one order alone wanted 10,398 Kilowatt Cases), Market.CSGO and Steam. It measures appetite for the name, not depth behind price — which itself counts only unconditional orders: what any example of the item can be sold into, not a bid needing one particular phase or float (a ★ Karambit | Doppler FN reports $1,230 on that basis while a Phase 4-with-seeds order stands at $1,460). Buff163, YouPin, C5Game and DMarket publish no demand figure (null means “not published”, not “zero”), and no marketplace publishes how many items are wanted at the top price itself.

Backwards rolling:
Once: get markets backwards from today, simply so we can 


every day get https://steamdataapi.com/api/v1/items/history   -d '{ "game": "cs2", "days": 1, "names": [], "currency": "USD"  }'
query through 100 items each, using the list 
-> query once per metric: Which daily value per market: close (default), low or avg.

-> this returns the actual sale quantity from steam; no statistics about sales quantity available from markets



What we need first:

- https://steamdataapi.com/api/v1/crates?type=case&images=1&with_items=true
- https://steamdataapi.com/api/v1/collections?game=cs2&with_items=true

-> save all collections, crates and for first time call 

- https://steamdataapi.com/api/v1/items/all?game=cs2&markets=1&variants=1&currency=USD&meta=true&images=true

-> once store all metadata, including images 

-> Build db up like this, should simply contain everything, not be performant as is


## Data we need:

"Static tables"
-> item table (item_id, hash_name, meta info and image)
-> collections table
-> crates&capsules table

-> depending on the degree of relationships (1->N / N:N ...) we might introduce relationship tables

Performance oriented tables:
use timescaledb
still save old intraday table values but switch underlying table every week so it doesn't get too big; depending on size, see if / how partitioning is needed or if timescaledb is enough

-> use marketHashName<->item_id and marketname<->market_id hashmap (stored in memory, not loaded new everytime) when storing data to significantly lower storage space

intraday tables (even though we query more often, only update if one of the values changed, not every time its been fetched): 

sell_orders: time(captured_at) item_id market_id lowest_ask quantity
buy_orders: time(captured_at) item_id market_id highest_bid demand

longterm tables:
daily prices = historic, once stored using historic list, to get old data. then built using the sell_orders (and buy_orders) table at end of every day

daily_prices: time(day) item_id market_id open_ask high_ask(-> highest lowest ask in the day) low_ask close_ask open_bid high_bid low_bid(-> lowest highest bid) close_bid ask_quantity bid_quantity (-> not sure what quantity metrics are important / we can accurately measure)


TODO: we also have to check if the seller / buyers fees have been deducted already, think about how we should handle that. (Store price + fees, only price without or both?)