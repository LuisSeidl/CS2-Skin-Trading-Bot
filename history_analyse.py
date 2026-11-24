# -*- coding: utf-8 -*-
"""
Datenqualität des Bulk-History-Endpunkts (POST /api/v1/items/history).

Liest nur Dateien aus data/steam_data_api (history_*.json, all_items*.json) und schreibt nichts.
Zellen mit "# %%" können einzeln in VS Code / PyCharm / Jupyter ausgeführt werden.
Prüfdimensionen wie im Paper: Vollständigkeit, Eindeutigkeit, Plausibilität, Aktualität,
Stabilität, externe Validität (Abgleich mit den eigenen Abrufen der Verkaufsangebote).
"""
# %% 0 Setup
import gc, json, re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
DATA = BASE / "data" / "steam_data_api"
HIST_FILE = sorted(DATA.glob("history_*.json"))[-1]
TS = re.compile(r"(\d{4}-\d{2}-\d{2})[ _](\d{2})[:_](\d{2})[:_](\d{2})")
pd.set_option("display.width", 200, "display.max_columns", 30)


def file_time(p):
    d, h, m, s = TS.search(p.name).groups()
    return pd.Timestamp(f"{d} {h}:{m}:{s}", tz="UTC")


def pct(x, nd=1):
    return f"{100 * x:.{nd}f} %"


# %% 1 History laden (lang: name, market, date, price, qty)
j = json.loads(HIST_FILE.read_text(encoding="utf-8"))
print("Datei:", HIST_FILE.name, "| metric:", j["metric"], "| currency:", j["currency"],
      "| requested:", j["requested"], "| matched:", j["matched"], "| missing:", len(j["missing"]))
rows = [(it["marketHashName"], m, p["date"], p["price"], p["quantity"])
        for it in j["data"] for m, pts in it["markets"].items() for p in pts]
h = pd.DataFrame(rows, columns=["name", "market", "date", "price", "qty"])
h["ts"] = pd.to_datetime(h["date"], utc=True)
h["day"] = h["ts"].dt.normalize()
sample_names = sorted(h["name"].unique())
del j, rows
print(f"{len(h):,} Punkte, {h.name.nunique()} Items, {h.market.nunique()} Marktplätze")

# %% 2 Vollständigkeit: Zeitraum je Marktplatz, Lücken, abgebrochene Reihen
g_first, g_last = h["day"].min(), h["day"].max()
print("Gesamter Zeitraum:", g_first.date(), "bis", g_last.date(), f"({(g_last - g_first).days + 1} Tage)")
cov = h.groupby("market").agg(punkte=("price", "size"), items=("name", "nunique"),
                              erster_tag=("day", "min"), letzter_tag=("day", "max"))
cov["tage_im_fenster"] = (cov["letzter_tag"] - cov["erster_tag"]).dt.days + 1
cov["erster_tag"] = cov["erster_tag"].dt.date
cov["letzter_tag"] = cov["letzter_tag"].dt.date
print(cov.sort_values("erster_tag").to_string())

s = h.sort_values(["name", "market", "day"]).copy()
s["gap"] = s.groupby(["name", "market"])["day"].diff().dt.days - 1          # fehlende Tage vor diesem Punkt
ser = s.groupby(["name", "market"]).agg(n=("day", "size"), first=("day", "min"), last=("day", "max"))
ser["span"] = (ser["last"] - ser["first"]).dt.days + 1
ser["fehlend"] = ser["span"] - ser["n"]
print(f"\nReihen (Item × Marktplatz): {len(ser):,}")
print("Reihen mit mindestens einer Lücke im Verlauf:", pct((ser["fehlend"] > 0).mean()),
      "| fehlende Tage insgesamt:", pct(ser["fehlend"].sum() / ser["span"].sum(), 2), "der Reihenspanne")
print("Größte Lücke je Reihe (Tage), Quantile:", s.groupby(["name", "market"])["gap"].max().fillna(0)
      .quantile([.5, .9, .99, 1]).to_dict())
print("Reihen, die vor dem letzten Tag enden:", pct((ser["last"] < g_last).mean()))
mstart = cov["erster_tag"].map(pd.Timestamp)
late = ser.reset_index().merge(mstart.rename("m_start"), left_on="market", right_index=True)
print("Reihen, die später als der Marktplatz-Beginn starten:", pct((late["first"] > late["m_start"].dt.tz_localize("UTC")).mean()))
per_item = ser.reset_index().groupby("name")["market"].nunique()
print("Marktplätze je Item (Quantile):", per_item.quantile([0, .1, .5, .9, 1]).to_dict())

# %% 3 Eindeutigkeit und Zeitstempel
print("Doppelte (Item, Marktplatz, Tag):", int(h.duplicated(["name", "market", "day"]).sum()))
print("Zeitstempel nicht auf 00:00:00 UTC:", int((h["ts"] != h["day"]).sum()))
print("Preis fehlt:", int(h["price"].isna().sum()), "| Menge fehlt:", int(h["qty"].isna().sum()))
print("Preis <= 0:", int((h["price"] <= 0).sum()), "| Menge <= 0:", int((h["qty"] <= 0).sum()),
      "| kleinster Preis (Cent):", int(h["price"].min()), "| größter:", int(h["price"].max()))
print("Nicht ganzzahlige Preise:", int((h["price"] % 1 != 0).sum()))

# %% 4 Plausibilität: Tagesänderungen, Fortschreibung, Ausreißer
s["ret"] = s.groupby(["name", "market"])["price"].transform(lambda x: np.log(x / x.shift()))
s["same_price"] = s["ret"] == 0
s["same_qty"] = s.groupby(["name", "market"])["qty"].diff() == 0
adj = s[s["gap"] == 0]                                                    # nur aufeinanderfolgende Tage
tab = adj.groupby("market").agg(
    tage=("ret", "size"),
    preis_unveraendert=("same_price", "mean"),
    preis_und_menge_unveraendert=("same_qty", lambda x: np.nan),
    med_abs_aend=("ret", lambda x: np.exp(x.abs().median()) - 1),
    p99_abs_aend=("ret", lambda x: np.exp(x.abs().quantile(.99)) - 1),
    sprung_ueber_2x=("ret", lambda x: (x.abs() > np.log(2)).mean()),
)
tab["preis_und_menge_unveraendert"] = adj.assign(b=adj["same_price"] & adj["same_qty"]).groupby("market")["b"].mean()
print((tab * 1).round(4).to_string())
allr = adj["ret"].abs()
print(f"\nInsgesamt: Preis unverändert {pct(adj['same_price'].mean())}, Preis und Menge unverändert "
      f"{pct((adj['same_price'] & adj['same_qty']).mean())}, Sprünge über 2x: {pct((allr > np.log(2)).mean(), 2)}, "
      f"über 10x: {int((allr > np.log(10)).sum())} Fälle")
# lange konstante Phasen (Verdacht auf Fortschreibung)
s["chg"] = (~s["same_price"].fillna(False)) | (s["gap"].fillna(0) > 0)
s["run"] = s.groupby(["name", "market"])["chg"].cumsum()
runs = s.groupby(["name", "market", "run"]).size()
print("Konstante Preis-Phasen >= 14 Tage:", int((runs >= 14).sum()), "von", len(runs), "Phasen;",
      "längste:", int(runs.max()), "Tage")
print("\nGrößte Tagessprünge (Beispiele):")
print(adj.loc[allr.nlargest(8).index, ["name", "market", "day", "price", "qty", "ret"]]
      .assign(faktor=lambda d: np.exp(d["ret"])).to_string())

# %% 5 Konsistenz zwischen Marktplätzen (ohne Steam: kein Echtgeld)
nz = h[h["market"] != "steam"]
piv = nz.pivot_table(index=["name", "day"], columns="market", values="price")
cnt = piv.notna().sum(axis=1)
mn, mx = piv.min(axis=1), piv.max(axis=1)
ratio = (mx / mn)[cnt >= 2]
print(f"Item-Tage mit >= 2 Marktplätzen: {len(ratio):,}")
print("max/min je Item-Tag, Quantile:", ratio.quantile([.5, .9, .99, .999, 1]).round(2).to_dict())
print("Anteil max/min > 5:", pct((ratio > 5).mean(), 2), "| > 10:", pct((ratio > 10).mean(), 3),
      "| größter Wert:", round(float(ratio.max()), 1))
rel = piv.div(piv.median(axis=1), axis=0)
print("\nPreis relativ zum Tages-Median über Marktplätze (Median je Marktplatz; < 1 = günstiger):")
print(rel.median().round(3).sort_values().to_string())
# zusätzlich: Steam-Preis relativ zu den anderen
st = h[h["market"] == "steam"].set_index(["name", "day"])["price"]
print("\nSteam / Median der anderen Marktplätze (Median):",
      round(float((st / piv.median(axis=1)).dropna().median()), 3))

# %% 6 Aktualität
print("Letzter Tag in der History:", g_last.date(), "| Datei erzeugt:", file_time(HIST_FILE))
print("Rückstand in Tagen:", (file_time(HIST_FILE).normalize() - g_last).days, "(heutiger Tag ist nicht enthalten)")

# %% 7 Eigene Abrufe der Verkaufsangebote laden (nur Items ohne Variante, wie in der Pipeline)
def load_sell(p):
    jj = json.loads(p.read_text(encoding="utf-8"))
    r, nvar, vnames = [], 0, set()
    for it in jj["data"]:
        if it.get("variants"):
            nvar += 1
            vnames.add(it["marketHashName"])
            continue
        for m in it.get("markets") or []:
            r.append((it["marketHashName"], m["market"], m["price"], m.get("quantity"), m["capturedAt"]))
    d = pd.DataFrame(r, columns=["name", "market", "price", "qty", "captured"])
    d["captured"] = pd.to_datetime(d["captured"], utc=True)
    return d, vnames


cands = sorted(DATA.glob("all_items*.json"), key=file_time)
pulls, last_t = [], None
for p in cands:                                   # Dubletten (< 5 Minuten Abstand) auslassen
    t = file_time(p)
    if last_t is None or (t - last_t) > pd.Timedelta("5min"):
        pulls.append(p)
        last_t = t
print("Abrufe:", [(file_time(p).strftime("%m-%d %H:%M"), p.stat().st_size // 10**6) for p in pulls])

# %% 8 Externe Validität: Tagesschlusskurs (close) gegen eigene Abrufe
H = h.set_index(["name", "market", "day"])[["price", "qty"]]
res, sem = [], []
for p in pulls:
    t = file_time(p)
    d, vn = load_sell(p)
    d = d[d["market"] != "steam"]
    cap_max = d["captured"].max()
    for off in (-1, 0, 1):                           # Tag vor, gleicher Tag, Folgetag
        day = t.normalize() + pd.Timedelta(days=off)
        if day not in set(h["day"]):
            continue
        hh = h[h["day"] == day][["name", "market", "price", "qty"]].rename(columns={"price": "h_price", "qty": "h_qty"})
        m = d.merge(hh, on=["name", "market"], how="inner")
        diff = (m["h_price"] - m["price"])
        rel = diff.abs() / m["price"]
        sem.append(dict(abruf=t.strftime("%m-%d %H:%M"), vergleichstag=day.date(), tag_offset=off, paare=len(m),
                        le_1cent=(diff.abs() <= 1).mean(), le_5pct=(rel <= .05).mean(),
                        med_abs_pct=rel.median(), menge_gleich=(m["h_qty"] == m["qty"]).mean()))
    gc.collect()
    print(t.strftime("%m-%d %H:%M"), "| capturedAt max:", cap_max.strftime("%m-%d %H:%M"),
          "| Varianten-Items:", len(vn), "| davon in Stichprobe:", len(vn & set(sample_names)))
    if t == file_time(pulls[-1]):
        last_pull = d
sem = pd.DataFrame(sem)
print(sem.round(4).to_string())

# %% 9 Externe Validität im Detail: je Marktplatz, letzter Abruf gegen letzten History-Tag
d = last_pull
day = g_last
hh = h[h["day"] == day][["name", "market", "price", "qty"]].rename(columns={"price": "h_price", "qty": "h_qty"})
m = d.merge(hh, on=["name", "market"], how="inner")
m["diff"] = m["h_price"] - m["price"]
m["rel"] = m["diff"].abs() / m["price"]
pm = m.groupby("market").agg(paare=("rel", "size"), le_1cent=("diff", lambda x: (x.abs() <= 1).mean()),
                             le_5pct=("rel", lambda x: (x <= .05).mean()), med_rel=("rel", "median"))
print(f"Abruf {file_time(pulls[-1]):%m-%d %H:%M} UTC gegen History-Tag {day.date()}")
print(pm.round(4).to_string())
print("\nÜbereinstimmung gleiche Items, aber unterschiedliche Marktplatzmengen (nur History):",
      sorted(set(h["market"]) - set(d["market"])), "| nur Abruf:", sorted(set(d["market"]) - set(h["market"])))
print("Größte Abweichungen:")
print(m.loc[m["rel"].nlargest(8).index, ["name", "market", "price", "h_price", "qty", "h_qty", "rel"]].to_string())

# %% 10 Repräsentativität der Stichprobe (die ersten 100 Namen?)
cat = sorted(set(last_pull["name"]))
pos = [cat.index(n) if n in cat else None for n in sample_names]
pos_ok = [x for x in pos if x is not None]
print("Stichprobe im Katalog gefunden:", len(pos_ok), "von", len(sample_names),
      "| Katalog-Positionen min/max:", min(pos_ok), max(pos_ok), "von", len(cat))
print("Erste/letzte Namen der Stichprobe:", sample_names[:2], sample_names[-2:])
med_all = last_pull[last_pull["market"] != "steam"].groupby("name")["price"].median()
print("Medianpreis (Cent) Katalog:", float(med_all.median()), "| Stichprobe:", float(med_all.reindex(sample_names).median()))
print("Preis-Quantile Katalog:", med_all.quantile([.1, .5, .9, .99]).round(0).to_dict())
print("Preis-Quantile Stichprobe:", med_all.reindex(sample_names).quantile([.1, .5, .9, .99]).round(0).to_dict())
