from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from database import db
from models import User, CollectionItem
from ops import now, clamp_placements

router = APIRouter(prefix="/api/locations")
KINDS = ("binder", "case", "box", "deck", "bulk", "other")


class LocIn(BaseModel):
    name: str
    kind: str = "box"
    description: str = ""


class LocPatch(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    description: Optional[str] = None


class PlaceIn(BaseModel):
    item_id: str
    quantity: int


class MoveIn(BaseModel):
    item_id: str
    from_id: str
    to_id: str
    quantity: int = 1


def _oid(v):
    if not ObjectId.is_valid(v):
        raise HTTPException(404, "Not found")
    return ObjectId(v)


async def _loc(uid, loc_id):
    d = await db.locations.find_one({"_id": _oid(loc_id), "user_id": uid})
    if not d:
        raise HTTPException(404, "Location not found")
    d["id"] = str(d.pop("_id"))
    return d


async def _item(uid, item_id):
    d = await db.collection_items.find_one({"_id": _oid(item_id), "user_id": uid})
    if not d:
        raise HTTPException(404, "Item not found")
    return d


def _unplaced(d):
    return d["quantity"] - sum((d.get("placements") or {}).values())


def _ser(d, qty):
    return {**CollectionItem.from_mongo(d).model_dump(), "placed": qty}


@router.get("")
async def list_locations(user: User = Depends(get_current_user)):
    locs = await db.locations.find({"user_id": user.id}).sort("created_at", 1).to_list(500)
    stats = {str(x["_id"]): {"cards": 0, "unique": 0, "value_gbp": 0.0} for x in locs}
    unassigned = {"cards": 0, "unique": 0, "value_gbp": 0.0}
    async for d in db.collection_items.find({"user_id": user.id}):
        for lid, q in (d.get("placements") or {}).items():
            if lid in stats and q > 0:
                s = stats[lid]
                s["cards"] += q; s["unique"] += 1; s["value_gbp"] += q * (d.get("price_gbp") or 0)
        u = _unplaced(d)
        if u > 0:
            unassigned["cards"] += u; unassigned["unique"] += 1; unassigned["value_gbp"] += u * (d.get("price_gbp") or 0)
    out = []
    for x in locs:
        lid = str(x["_id"])
        out.append({"id": lid, "name": x["name"], "kind": x["kind"], "description": x.get("description", ""),
                    **stats[lid], "value_gbp": round(stats[lid]["value_gbp"], 2)})
    unassigned["value_gbp"] = round(unassigned["value_gbp"], 2)
    return {"locations": out, "unassigned": unassigned}


@router.post("")
async def create_location(body: LocIn, user: User = Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(400, "Please enter a name")
    if body.kind not in KINDS:
        raise HTTPException(400, "Invalid kind")
    doc = {"user_id": user.id, "name": body.name.strip(), "kind": body.kind, "description": body.description,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.locations.insert_one(doc)
    return {"id": str(res.inserted_id), "name": doc["name"], "kind": doc["kind"], "description": doc["description"]}


@router.patch("/{loc_id}")
async def update_location(loc_id: str, body: LocPatch, user: User = Depends(get_current_user)):
    await _loc(user.id, loc_id)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "kind" in upd and upd["kind"] not in KINDS:
        raise HTTPException(400, "Invalid kind")
    if "name" in upd and not upd["name"].strip():
        raise HTTPException(400, "Please enter a name")
    if upd:
        await db.locations.update_one({"_id": ObjectId(loc_id)}, {"$set": upd})
    return await _loc(user.id, loc_id)


@router.delete("/{loc_id}")
async def delete_location(loc_id: str, user: User = Depends(get_current_user)):
    await _loc(user.id, loc_id)
    await db.locations.delete_one({"_id": ObjectId(loc_id)})
    await db.collection_items.update_many({"user_id": user.id}, {"$unset": {f"placements.{loc_id}": ""}})
    return {"ok": True}


@router.get("/unassigned/items")
async def unassigned_items(user: User = Depends(get_current_user)):
    docs = await db.collection_items.find({"user_id": user.id}).sort([("set_id", 1), ("local_num", 1)]).to_list(5000)
    return [_ser(d, _unplaced(d)) for d in docs if _unplaced(d) > 0]


@router.get("/{loc_id}")
async def location_detail(loc_id: str, user: User = Depends(get_current_user)):
    loc = await _loc(user.id, loc_id)
    docs = await db.collection_items.find({"user_id": user.id, f"placements.{loc_id}": {"$gt": 0}}).sort([("set_id", 1), ("local_num", 1)]).to_list(5000)
    items = [_ser(d, d["placements"][loc_id]) for d in docs]
    return {"location": loc, "items": items, "cards": sum(i["placed"] for i in items),
            "value_gbp": round(sum(i["placed"] * (i["price_gbp"] or 0) for i in items), 2)}


@router.post("/{loc_id}/place")
async def place(loc_id: str, body: PlaceIn, user: User = Depends(get_current_user)):
    await _loc(user.id, loc_id)
    d = await _item(user.id, body.item_id)
    pl = dict(d.get("placements") or {})
    others = sum(v for k, v in pl.items() if k != loc_id)
    if body.quantity < 0 or body.quantity + others > d["quantity"]:
        raise HTTPException(400, f"You only have {d['quantity'] - others} copies free to place here")
    pl[loc_id] = body.quantity
    pl = {k: v for k, v in pl.items() if v > 0}
    await db.collection_items.update_one({"_id": d["_id"]}, {"$set": {"placements": pl, "updated_at": now()}})
    return {"ok": True, "placements": pl}


@router.post("/move")
async def move(body: MoveIn, user: User = Depends(get_current_user)):
    d = await _item(user.id, body.item_id)
    pl = dict(d.get("placements") or {})
    for lid in (body.from_id, body.to_id):
        if lid != "unassigned":
            await _loc(user.id, lid)
    avail = _unplaced(d) if body.from_id == "unassigned" else pl.get(body.from_id, 0)
    if body.quantity < 1 or body.quantity > avail:
        raise HTTPException(400, "Not enough copies there to move")
    if body.from_id != "unassigned":
        pl[body.from_id] -= body.quantity
    if body.to_id != "unassigned":
        pl[body.to_id] = pl.get(body.to_id, 0) + body.quantity
    pl = {k: v for k, v in pl.items() if v > 0}
    await db.collection_items.update_one({"_id": d["_id"]}, {"$set": {"placements": pl, "updated_at": now()}})
    await clamp_placements({"_id": d["_id"]})
    return {"ok": True, "placements": pl}
