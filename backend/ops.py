from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

import tcgdex
from database import db


def now():
    return datetime.now(timezone.utc).isoformat()


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def owned_map(uid, query=None):
    out = {}
    async for d in db.collection_items.find({"user_id": uid, **(query or {})}, {"card_id": 1, "variant": 1, "quantity": 1}):
        out.setdefault(d["card_id"], {})[d["variant"]] = d["quantity"]
    return out


async def add_item(uid, card_id, variant, qty, location_id=None):
    card = await tcgdex.get_card(db, card_id)
    if not card:
        raise HTTPException(404, f"Card {card_id} not found")
    meta = tcgdex.summarize(card)
    meta.pop("card_id")
    inc = {"quantity": qty}
    if location_id:
        if not ObjectId.is_valid(location_id) or not await db.locations.find_one({"_id": ObjectId(location_id), "user_id": uid}):
            raise HTTPException(404, "Location not found")
        inc[f"placements.{location_id}"] = qty
    await db.collection_items.update_one(
        {"user_id": uid, "card_id": card_id, "variant": variant},
        {"$inc": inc, "$set": {**tcgdex.price_for(card, variant), "updated_at": now()},
         "$setOnInsert": {**meta, "condition": "NM", "created_at": now()}}, upsert=True)
    return meta["name"]


async def clamp_placements(flt):
    d = await db.collection_items.find_one(flt)
    if not d or not d.get("placements"):
        return
    pl = dict(d["placements"])
    over = sum(pl.values()) - d["quantity"]
    for k in sorted(pl, key=lambda k: pl[k]):
        if over <= 0:
            break
        take = min(over, pl[k])
        pl[k] -= take
        over -= take
    await db.collection_items.update_one({"_id": d["_id"]}, {"$set": {"placements": {k: v for k, v in pl.items() if v > 0}}})


async def collection_stats(uid):
    agg = await db.collection_items.aggregate([{"$match": {"user_id": uid}}, {"$group": {
        "_id": None, "qty": {"$sum": "$quantity"}, "unique": {"$addToSet": "$card_id"}, "sets": {"$addToSet": "$set_id"},
        "usd": {"$sum": {"$multiply": [{"$ifNull": ["$price_usd", 0]}, "$quantity"]}},
        "eur": {"$sum": {"$multiply": [{"$ifNull": ["$price_eur", 0]}, "$quantity"]}},
        "gbp": {"$sum": {"$multiply": [{"$ifNull": ["$price_gbp", 0]}, "$quantity"]}}}}]).to_list(1)
    a = agg[0] if agg else {}
    return {"total_cards": a.get("qty", 0), "unique_cards": len(a.get("unique", [])), "sets_started": len(a.get("sets", [])),
            "value_usd": round(a.get("usd", 0), 2), "value_eur": round(a.get("eur", 0), 2), "value_gbp": round(a.get("gbp", 0), 2)}
