import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

import tcgdex
from auth import get_current_user
from database import db
from models import User
from ops import today, collection_stats

router = APIRouter(prefix="/api")
log = logging.getLogger("history")


async def record_card_prices(card):
    prices = {v: tcgdex.price_for(card, v) for v in tcgdex.variants_of(card)}
    await db.card_price_history.update_one({"card_id": card["id"], "date": today()}, {"$set": {"prices": prices}}, upsert=True)


async def snapshot_user(uid):
    st = await collection_stats(uid)
    await db.value_history.update_one({"user_id": uid, "date": today()}, {"$set": {
        "value_usd": st["value_usd"], "value_eur": st["value_eur"], "value_gbp": st["value_gbp"],
        "total_cards": st["total_cards"]}}, upsert=True)


async def migrate_gbp():
    for coll in (db.collection_items, db.wishlist):
        async for d in coll.find({"price_gbp": None}, {"price_usd": 1, "price_eur": 1}):
            await coll.update_one({"_id": d["_id"]}, {"$set": {"price_gbp": tcgdex.to_gbp(d.get("price_usd"), d.get("price_eur"))}})
    async for d in db.value_history.find({"value_gbp": None}):
        await db.value_history.update_one({"_id": d["_id"]}, {"$set": {"value_gbp": tcgdex.to_gbp(d.get("value_usd"), d.get("value_eur"))}})


async def daily_job():
    await tcgdex.refresh_fx(db)
    ids = set(await db.collection_items.distinct("card_id")) | set(await db.wishlist.distinct("card_id"))
    for cid in ids:
        try:
            card = await tcgdex.get_card(db, cid, ttl=20 * 3600)
            if not card:
                continue
            await record_card_prices(card)
            async for d in db.collection_items.find({"card_id": cid}, {"variant": 1}):
                await db.collection_items.update_one({"_id": d["_id"]}, {"$set": tcgdex.price_for(card, d["variant"])})
        except Exception as e:  # noqa
            log.warning("daily price %s failed: %s", cid, e)
    async for u in db.users.find({}, {"_id": 1}):
        await snapshot_user(str(u["_id"]))
    await db.app_meta.update_one({"_id": "daily_job"}, {"$set": {"date": today()}}, upsert=True)


async def daily_loop():
    while True:
        try:
            meta = await db.app_meta.find_one({"_id": "daily_job"})
            if not meta or meta.get("date") != today():
                await daily_job()
        except Exception as e:  # noqa
            log.warning("daily job failed: %s", e)
        await asyncio.sleep(3600)


def _shift(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


@router.get("/cards/{card_id}/history")
async def card_history(card_id: str, user: User = Depends(get_current_user)):
    card = await tcgdex.get_card(db, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    points = []
    async for d in db.card_price_history.find({"card_id": card_id}).sort("date", 1):
        p = {"date": d["date"]}
        for v, pr in d["prices"].items():
            p[f"{v}_usd"], p[f"{v}_eur"], p[f"{v}_gbp"] = pr.get("price_usd"), pr.get("price_eur"), pr.get("price_gbp")
        points.append(p)
    cm = (card.get("pricing") or {}).get("cardmarket") or {}
    trend = [{"date": _shift(days), "normal": tcgdex.to_gbp(eur=cm.get(k)), "holo": tcgdex.to_gbp(eur=cm.get(f"{k}-holo"))}
             for days, k in ((30, "avg30"), (7, "avg7"), (1, "avg1"), (0, "trend"))]
    trend = [t for t in trend if t["normal"] is not None or t["holo"] is not None]
    return {"points": points, "variants": tcgdex.variants_of(card), "cardmarket_trend": trend}


@router.get("/collection/history")
async def collection_history(days: int = 365, user: User = Depends(get_current_user)):
    await snapshot_user(user.id)
    docs = await db.value_history.find({"user_id": user.id, "date": {"$gte": _shift(days)}}, {"_id": 0, "user_id": 0}).sort("date", 1).to_list(2000)
    return docs
