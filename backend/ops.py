from datetime import datetime, timezone

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


async def add_item(uid, card_id, variant, qty):
    card = await tcgdex.get_card(db, card_id)
    if not card:
        raise HTTPException(404, f"Card {card_id} not found")
    meta = tcgdex.summarize(card)
    meta.pop("card_id")
    await db.collection_items.update_one(
        {"user_id": uid, "card_id": card_id, "variant": variant},
        {"$inc": {"quantity": qty}, "$set": {**tcgdex.price_for(card, variant), "updated_at": now()},
         "$setOnInsert": {**meta, "condition": "NM", "created_at": now()}}, upsert=True)
    return meta["name"]


async def collection_stats(uid):
    agg = await db.collection_items.aggregate([{"$match": {"user_id": uid}}, {"$group": {
        "_id": None, "qty": {"$sum": "$quantity"}, "unique": {"$addToSet": "$card_id"}, "sets": {"$addToSet": "$set_id"},
        "usd": {"$sum": {"$multiply": [{"$ifNull": ["$price_usd", 0]}, "$quantity"]}},
        "eur": {"$sum": {"$multiply": [{"$ifNull": ["$price_eur", 0]}, "$quantity"]}}}}]).to_list(1)
    a = agg[0] if agg else {}
    return {"total_cards": a.get("qty", 0), "unique_cards": len(a.get("unique", [])), "sets_started": len(a.get("sets", [])),
            "value_usd": round(a.get("usd", 0), 2), "value_eur": round(a.get("eur", 0), 2)}
