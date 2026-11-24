# Analyse der Ankaufsangebote (Gebote) - als Zellen für VS Code / Jupyter ("# %%" = neue Zelle).
# Läuft auch direkt: python ankauf_analyse.py   (liest nur aus data/steam_data_api, schreibt nichts)
# Pulls: A = 23.11. 19:27, B = 23.11. 19:32 (4 min später), C = 24.11. 06:55 (11,4 h später); Verkaufsabruf D = 24.11. 06:57

# %% Laden: eine Zeile pro (Item, Markt) mit der Abrufzeit der jeweiligen Seite (steht im Dateinamen, UTC)
import json, re
from pathlib import Path
import numpy as np, pandas as pd
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)

BASE = Path(__file__).parent / "data" / "steam_data_api" if "__file__" in globals() else Path("data/steam_data_api")
PULLS = {"A": BASE / "buy_orders_2026-11-23 19:27", "B": BASE / "buy_orders_2026-11-23 19:32", "C": BASE / "buy_orders_2026-11-24 07:54"}
SELL = BASE / "all_items__2026-11-24 06:57:25.507588.json"

def load_pull(folder):
    rows = []
    for f in sorted(folder.iterdir()):
        j = json.load(open(f))
        t = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)", f.name).group(1)
        for it in j.get("data") or []:
            best, ask = it.get("best") or {}, it.get("ask") or {}
            for bo in it.get("buyOrders") or []:
                rows.append((it["marketHashName"], bo["market"], bo["price"], bo.get("demand"), bo["capturedAt"], j["page"], t,
                             best.get("price"), ask.get("price"), it.get("spread"), it.get("marketCount")))
    df = pd.DataFrame(rows, columns=["name", "market", "price", "qty", "capturedAt", "page", "requested_at",
                                     "best_price", "ask_price", "spread", "marketCount"])
    df["capturedAt"] = pd.to_datetime(df["capturedAt"], utc=True)
    df["requested_at"] = pd.to_datetime(df["requested_at"], utc=True)
    return df

raw = {k: load_pull(p) for k, p in PULLS.items()}

# %% 1. Eindeutigkeit (inkl. Steam, vor der Bereinigung)
for k, df in raw.items():
    key = ["name", "market"]
    dup = df.duplicated(key, keep=False)
    g = df[dup].groupby(key).agg(npr=("price", "nunique"), ncap=("capturedAt", "nunique"))
    pages = df[dup].groupby("name")["page"].agg(lambda s: s.max() - s.min())
    print(k, "Zeilen", len(df), "| doppelte Schlüssel", len(g), "| davon mit abweichendem Preis/Zeitstempel", int(((g.npr > 1) | (g.ncap > 1)).sum()),
          "| Items mehrfach über Seiten:", df.groupby("name")["page"].nunique().gt(1).sum(), "| Seitenabstand:", pages.value_counts().head(3).to_dict())

# Bereinigung: pro (Item, Markt) gewinnt der jüngste capturedAt (drop_duplicates() allein lässt die abweichenden Paare stehen)
def clean(df):
    return df.sort_values("capturedAt").drop_duplicates(["name", "market"], keep="last")
bids = {k: clean(df) for k, df in raw.items()}
bids_ns = {k: df[df.market != "steam"] for k, df in bids.items()}          # ohne Steam (kein Echtgeld)
print({k: int(df.duplicated(["name", "market"]).sum()) for k, df in bids.items()}, "<- Duplikate nach Bereinigung")

# %% 2. Vollständigkeit
for k, df in bids_ns.items():
    n = df.groupby("name")["market"].nunique()
    print(k, "Gebote", len(df), "| Items", n.size, "| auf >= 2 Märkten", int((n >= 2).sum()), "| #Märkte je Item", n.value_counts().sort_index().to_dict())
print("Gebote je Markt (C):", bids_ns["C"]["market"].value_counts().to_dict())

# %% 3. Aktualität: Alter = Abrufzeit DER SEITE minus capturedAt (eine feste Abrufzeit liefert negative Alter, weil das Abrufen von 61 Seiten ~2,5 min dauert)
for k, df in bids_ns.items():
    age = (df.requested_at - df.capturedAt).dt.total_seconds()
    age1 = (df.requested_at.min() - df.capturedAt).dt.total_seconds()
    print(k, "pro Seite: Median %.0fs  q90 %.0fs  q99 %.0fs  max %.0fs | feste Abrufzeit: Median %.0fs  negativ %.1f %%" %
          (age.median(), age.quantile(.9), age.quantile(.99), age.max(), age1.median(), (age1 < 0).mean() * 100))
print("verschiedene capturedAt je Markt (C):", bids_ns["C"].groupby("market")["capturedAt"].nunique().to_dict())

# %% 4. Plausibilität: Gebot gegen Angebot auf demselben Markt (Items ohne Variante, C gegen D)
sj = json.load(open(SELL))
rows = [(it["marketHashName"], m["market"], m["price"], m["capturedAt"]) for it in sj["data"] if not it.get("variants") for m in it.get("markets") or []]
asks = pd.DataFrame(rows, columns=["name", "market", "ask", "ask_captured"])
asks["ask_captured"] = pd.to_datetime(asks["ask_captured"], utc=True)
asks.loc[asks.ask == 0, "ask"] = 1

x = bids_ns["C"].merge(asks, on=["name", "market"])
x = x[(x.price > 0) & (x.ask > 0)].copy()
x["gap"] = (x.ask - x.price) / x.ask * 100          # nach oben auf 100 % beschränkt
print("Paare", len(x), "| Gebot > Angebot:", int((x.price > x.ask).sum()), "| Gebot == Angebot:", int((x.price == x.ask).sum()),
      "| gleicher capturedAt:", round((x.capturedAt == x.ask_captured).mean(), 3))
print(x.groupby("market")["gap"].describe(percentiles=[.25, .5, .75]).round(1))
x["bucket"] = pd.qcut(x.ask, 6, duplicates="drop")
print(x.groupby("bucket", observed=True).agg(n=("gap", "size"), gleich=("price", lambda v: (v == x.loc[v.index, "ask"]).mean()), median_gap=("gap", "median")).round(2))

# %% 5. Streuung der Gebote zwischen Märkten (C, ohne Steam). min/max-Spread ist hier NICHT aussagekräftig: Gebote bis 1 Cent
s = (bids_ns["C"][bids_ns["C"].price > 0].groupby("name")["price"]
     .agg(n="count", top="max", low="min", med="median", q1=lambda v: v.quantile(.25), q3=lambda v: v.quantile(.75),
          second=lambda v: v.nlargest(2).iloc[-1] if len(v) > 1 else np.nan).reset_index())
s = s[s.n >= 2].copy()
s["rel"] = (s.top - s.low) / s.low * 100
s["sym"] = (s.top - s.low) / ((s.top + s.low) / 2) * 100
s["iqr"] = (s.q3 - s.q1) / s.med * 100
s["gap_top"] = (s.top - s.second) / s.second * 100       # höchstes vs. zweithöchstes Gebot
s["top_over_second"] = s.top / s.second
print(len(s), "Items");  print(s[["rel", "sym", "iqr", "gap_top", "top_over_second"]].describe(percentiles=[.5, .9, .99]).round(1))
print("Items mit niedrigstem Gebot = 1 Cent:", int((s.low == 1).sum()), "| höchstes >= 2x zweithöchstes:", round((s.top_over_second >= 2).mean(), 4),
      "| >= 5x:", round((s.top_over_second >= 5).mean(), 4), "| Maximum:", round(s.top_over_second.max(), 1))

# %% 6. Konsistenz mit den Aggregaten des Anbieters (C)
it = bids["C"].drop_duplicates("name")[["name", "best_price", "ask_price", "spread", "marketCount"]]
mx = bids_ns["C"].groupby("name").price.max().rename("max_ns"); mx_all = bids["C"].groupby("name").price.max().rename("max_all")
nm = bids["C"].groupby("name").market.nunique().rename("n_all"); nm_ns = bids_ns["C"].groupby("name").market.nunique().rename("n_ns")
c = it.merge(mx, on="name", how="left").merge(mx_all, on="name").merge(nm, on="name").merge(nm_ns, on="name", how="left")
print("best_price == höchstes Gebot ohne Steam:", round((c.best_price == c.max_ns).mean(), 4), "| inkl. Steam:", round((c.best_price == c.max_all).mean(), 4))
print("spread == ask_price - best_price:", round(((c.ask_price - c.best_price) == c.spread).mean(), 4))
print("marketCount == #Märkte inkl. Steam:", round((c.marketCount == c.n_all).mean(), 4), "| ohne Steam:", round((c.marketCount == c.n_ns).mean(), 4))

# %% 7. Stabilität und Volatilität (A->B kurz, B->C lang), je Markt
st = {"A": pd.Timestamp("2026-11-23 19:27:36", tz="UTC"), "B": pd.Timestamp("2026-11-23 19:31:48", tz="UTC"), "C": pd.Timestamp("2026-11-24 06:54:53", tz="UTC")}
for a, b in (("A", "B"), ("B", "C")):
    m = bids_ns[a].merge(bids_ns[b], on=["name", "market"], suffixes=("_a", "_b"))
    ch = m.price_a != m.price_b
    rel = ((m.price_b - m.price_a).abs() / m.price_a)[ch]
    q = m[m.qty_a.notna() & m.qty_b.notna()]
    print(f"{a}->{b} Abstand {st[b]-st[a]} | gemeinsam {len(m)} | nur in {a}: {len(bids_ns[a])-len(m)}, nur in {b}: {len(bids_ns[b])-len(m)} | "
          f"Preis geändert {ch.sum()} ({ch.mean()*100:.1f} %), hoch {(m.price_b>m.price_a).sum()}, runter {(m.price_b<m.price_a).sum()} | Median |Änderung| {rel.median()*100:.1f} % | "
          f"Menge geändert {(q.qty_a!=q.qty_b).mean()*100:.1f} %")
    print("   Preis geändert je Markt:", m.assign(ch=ch).groupby("market")["ch"].mean().round(3).to_dict())
