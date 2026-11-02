-- This script could be used to create a materialized view, that always shows the best possible arbitrages

with adjusted_prices as (
SELECT 
        item_id,
        platform,
        (ask + (ask *pf.buying_fee)/100 ) as buying_price, --if we buy, we have to add the buying fee, to get our costs
        ask_volume as buying_volume,
        ( bid - (bid * pf.selling_fee)/100 ) as selling_price, --we sell it, so we have to reduce it by the fee to get our payout
        bid_volume as selling_volume
      FROM tmp_items_prices tip join platform_fees pf on tip.platform = pf.platform_name
),
ranked_prices AS (
    SELECT 
        item_id,
        platform,
        buying_price,
        buying_volume,
        selling_price,
        selling_volume,
        ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY (buying_price) ASC NULLS LAST) as ask_rank,
        ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY (selling_price) DESC NULLS LAST) as bid_rank
    FROM adjusted_prices
),
lowest_asks AS (
    SELECT item_id, platform, buying_price, buying_volume FROM ranked_prices WHERE ask_rank = 1
),
highest_bids AS (
    SELECT item_id, platform, selling_price, selling_volume FROM ranked_prices WHERE bid_rank = 1
),
all_profits as (
SELECT 
    a.item_id,
    ti.market_hash_name ,
    a.platform AS ask_platform,
    a.buying_price,
    a.buying_volume,
    (b.selling_price - a.buying_price) as profit,
    (((b.selling_price - a.buying_price) / b.selling_price )*100) as profit_perc,
    b.platform AS bid_platform,
    b.selling_price,
    b.selling_volume
FROM lowest_asks a
JOIN highest_bids b ON a.item_id = b.item_id
JOIN tmp_items ti ON a.item_id = ti.id 
WHERE b.selling_price > a.buying_price
)
select * from all_profits order by profit desc nulls last; 


