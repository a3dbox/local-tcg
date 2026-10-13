import os
import re
import json
import time
import asyncio
from urllib.parse import urlencode

import httpx

BASE = os.environ["TCGDEX_BASE"]
POKEAPI = os.environ["POKEAPI_BASE"]
FX_BASE = os.environ["FX_BASE"]
SYMBOL_BASE = os.environ["SYMBOL_BASE"]
FX = {"eur_gbp": None, "usd_gbp": None}
DAY = 24 * 3600
http = httpx.AsyncClient(timeout=30, headers={"User-Agent": "PokeBinder/1.0"}, follow_redirects=True)
_sem = asyncio.Semaphore(8)

VARIANT_LABELS = {"normal": "Normal", "holo": "Holo", "reverse": "Reverse Holo",
                  "firstEdition": "1st Edition", "wPromo": "W Promo"}
TCP_KEYS = {"normal": ["normal", "unlimited", "unlimited-normal"],
            "holo": ["holofoil", "unlimited-holofoil"],
            "reverse": ["reverse-holofoil", "reverse"],
            "firstEdition": ["1st-edition-holofoil", "1st-edition-normal", "1st-edition", "1stEditionHolofoil"],
            "wPromo": ["normal", "holofoil"]}


async def fetch_url(db, url, params=None, ttl=DAY):
    key = url + "?" + urlencode(sorted((params or {}).items()))
    doc = await db.api_cache.find_one({"_id": key})
    if doc and doc["ts"] > time.time() - ttl:
        return json.loads(doc["data"])
    try:
        async with _sem:
            r = await http.get(url, params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError):
        if doc:
            return json.loads(doc["data"])
        raise
    await db.api_cache.replace_one({"_id": key}, {"_id": key, "data": json.dumps(data), "ts": time.time()}, upsert=True)
    return data


async def fetch(db, path, params=None, ttl=DAY):
    return await fetch_url(db, BASE + path, params, ttl)


async def get_card(db, card_id, ttl=6 * 3600):
    return await fetch(db, f"/cards/{card_id}", ttl=ttl)


async def get_set(db, set_id):
    return await fetch(db, f"/sets/{set_id}", ttl=12 * 3600)


async def all_sets(db):
    return await fetch(db, "/sets", ttl=12 * 3600) or []


def to_int(s):
    m = re.match(r"^0*(\d+)$", str(s or ""))
    return int(m.group(1)) if m else None


def search_params(q=None, set_id=None, type=None, rarity=None, category=None, dex=None, illustrator=None, exact=False, sort=None):
    p = {}
    if q:
        p["name"] = f"eq:{q}" if exact else q
    if set_id:
        p["set.id"] = f"eq:{set_id}"
    if type:
        p["types"] = type
    if rarity:
        p["rarity"] = f"eq:{rarity}"
    if category:
        p["category"] = category
    if dex:
        p["dexId"] = f"eq:{dex}"
    if illustrator:
        p["illustrator"] = illustrator
    if sort:
        p["sort:field"] = sort.lstrip("-")
        p["sort:order"] = "DESC" if sort.startswith("-") else "ASC"
    return p


def symbol_url(set_id: str) -> str:
    sid = re.sub(r"^([a-z]+)0+(\d)", r"\1\2", set_id.lower())
    sid = sid.replace(".5", "pt5") if sid.startswith(("sv", "me")) else sid.replace(".", "")
    return f"{SYMBOL_BASE}/{sid}/symbol.png"


def variants_of(card) -> list:
    out = []
    for v in card.get("variants_detailed") or []:
        t = v.get("type")
        t = {"firstedition": "firstEdition", "1stEdition": "firstEdition"}.get(t, t)
        if t and t not in out:
            out.append(t)
    if not out:
        out = [k for k, on in (card.get("variants") or {}).items() if on]
    return out or ["normal"]


async def refresh_fx(db):
    d = await fetch_url(db, f"{FX_BASE}/latest", {"base": "EUR", "symbols": "GBP,USD"}, ttl=12 * 3600)
    if d and d.get("rates", {}).get("GBP") and d["rates"].get("USD"):
        FX["eur_gbp"] = d["rates"]["GBP"]
        FX["usd_gbp"] = d["rates"]["GBP"] / d["rates"]["USD"]
    return FX


def to_gbp(usd=None, eur=None):
    if eur is not None and FX["eur_gbp"]:
        return round(eur * FX["eur_gbp"], 2)
    if usd is not None and FX["usd_gbp"]:
        return round(usd * FX["usd_gbp"], 2)
    return None


def price_for(card, variant) -> dict:
    p = card.get("pricing") or {}
    tp = p.get("tcgplayer") or {}
    usd = None
    for k in TCP_KEYS.get(variant, []):
        e = tp.get(k)
        if isinstance(e, dict):
            usd = e.get("marketPrice") or e.get("midPrice")
            if usd:
                break
    if usd is None:
        for e in tp.values():
            if isinstance(e, dict) and (e.get("marketPrice") or e.get("midPrice")):
                usd = e.get("marketPrice") or e.get("midPrice")
                break
    cm = p.get("cardmarket") or {}
    eur = None
    if variant in ("holo", "reverse"):
        eur = cm.get("trend-holo") or cm.get("avg-holo")
    eur = eur or cm.get("trend") or cm.get("avg")
    return {"price_usd": usd, "price_eur": eur, "price_gbp": to_gbp(usd, eur)}


def summarize(card) -> dict:
    s = card.get("set") or {}
    return {"card_id": card["id"], "set_id": s.get("id"), "set_name": s.get("name"), "name": card.get("name") or "",
            "local_id": str(card.get("localId") or ""), "local_num": to_int(card.get("localId")),
            "image": card.get("image"), "rarity": card.get("rarity"), "category": card.get("category"),
            "types": card.get("types") or []}


def progress(sd, owned: dict) -> dict:
    cc = sd.get("cardCount") or {}
    cards = sd.get("cards") or []
    total = cc.get("total") or len(cards)
    official = cc.get("official") or total
    lid = {c["id"]: to_int(c.get("localId")) for c in cards}
    have_full = sum(1 for cid in owned if cid in lid)
    have_base = sum(1 for cid in owned if cid in lid and lid[cid] is not None and lid[cid] <= official)
    master_total = sum(cc.get(k) or 0 for k in ("normal", "holo", "reverse", "firstEd")) or total
    have_master = sum(len(v) for cid, v in owned.items() if cid in lid)
    return {"base": [min(have_base, official), official], "full": [have_full, total],
            "master": [min(have_master, master_total), master_total]}
