from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from database import db
from models import User
from ops import add_item, now

router = APIRouter(prefix="/api/family")


class GiveIn(BaseModel):
    to_user_id: str
    card_id: str
    variant: str
    quantity: int = 1


async def _cards(uid):
    out = {}
    async for d in db.collection_items.find({"user_id": uid}):
        c = out.setdefault(d["card_id"], {"card_id": d["card_id"], "name": d["name"], "image": d.get("image"),
                                          "set_id": d.get("set_id"), "set_name": d.get("set_name"),
                                          "local_id": d.get("local_id"), "qty": 0, "variants": {}, "price_usd": None})
        c["qty"] += d["quantity"]
        c["variants"][d["variant"]] = d["quantity"]
        if d.get("price_usd") is not None:
            c["price_usd"] = max(c["price_usd"] or 0, d["price_usd"])
    return out


async def _goal_sets(uid):
    return {g["set_id"] async for g in db.goals.find({"user_id": uid})}


def _give_list(src, dst, dst_goals):
    out = []
    for cid, c in src.items():
        if c["qty"] > 1 and cid not in dst:
            spare = max(c["variants"].items(), key=lambda kv: kv[1])
            out.append({**c, "spare_variant": spare[0], "spare_qty": spare[1] - 1 if len(c["variants"]) == 1 else c["qty"] - 1,
                        "needed_for_goal": c["set_id"] in dst_goals})
    return sorted(out, key=lambda x: (not x["needed_for_goal"], -(x["price_usd"] or 0)))


@router.get("/members")
async def members(user: User = Depends(get_current_user)):
    out = []
    async for u in db.users.find({"_id": {"$ne": ObjectId(user.id)}}, {"name": 1}):
        uid = str(u["_id"])
        n = await db.collection_items.count_documents({"user_id": uid})
        out.append({"id": uid, "name": u["name"], "items": n})
    return out


@router.get("/compare/{other_id}")
async def compare(other_id: str, user: User = Depends(get_current_user)):
    other = await db.users.find_one({"_id": ObjectId(other_id)}) if ObjectId.is_valid(other_id) else None
    if not other or other_id == user.id:
        raise HTTPException(404, "Member not found")
    mine, theirs = await _cards(user.id), await _cards(other_id)
    my_goals, their_goals = await _goal_sets(user.id), await _goal_sets(other_id)
    return {"other": {"id": other_id, "name": other["name"]},
            "counts": {"shared": len(mine.keys() & theirs.keys()), "only_me": len(mine.keys() - theirs.keys()),
                       "only_them": len(theirs.keys() - mine.keys())},
            "i_can_give": _give_list(mine, theirs, their_goals),
            "they_can_give": _give_list(theirs, mine, my_goals)}


@router.post("/give")
async def give(body: GiveIn, user: User = Depends(get_current_user)):
    if body.to_user_id == user.id or not ObjectId.is_valid(body.to_user_id):
        raise HTTPException(400, "Invalid recipient")
    to = await db.users.find_one({"_id": ObjectId(body.to_user_id)})
    if not to:
        raise HTTPException(404, "Member not found")
    qty = max(1, body.quantity)
    flt = {"user_id": user.id, "card_id": body.card_id, "variant": body.variant}
    item = await db.collection_items.find_one(flt)
    if not item or item["quantity"] < qty:
        raise HTTPException(400, "You don't have enough copies to give")
    if item["quantity"] == qty:
        await db.collection_items.delete_one(flt)
    else:
        await db.collection_items.update_one(flt, {"$inc": {"quantity": -qty}, "$set": {"updated_at": now()}})
    await add_item(body.to_user_id, body.card_id, body.variant, qty)
    await db.trade_log.insert_one({"from_id": user.id, "from_name": user.name, "to_id": body.to_user_id, "to_name": to["name"],
                                   "card_id": body.card_id, "name": item["name"], "image": item.get("image"),
                                   "variant": body.variant, "quantity": qty, "created_at": now()})
    return {"ok": True}


@router.get("/activity")
async def activity(user: User = Depends(get_current_user)):
    return await db.trade_log.find({"$or": [{"from_id": user.id}, {"to_id": user.id}]}, {"_id": 0}).sort("created_at", -1).to_list(30)
