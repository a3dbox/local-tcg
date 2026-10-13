from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os  # noqa: E402
import io  # noqa: E402
import csv  # noqa: E402
import asyncio  # noqa: E402
import logging  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Optional, List  # noqa: E402

from bson import ObjectId  # noqa: E402
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

import tcgdex  # noqa: E402
import scanner  # noqa: E402
from auth import router as auth_router, get_current_user, seed_admin  # noqa: E402
from database import db, client  # noqa: E402
from models import User, CollectionItem  # noqa: E402

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="PokeBinder")
api = APIRouter(prefix="/api")


def now():
    return datetime.now(timezone.utc).isoformat()


async def owned_map(uid, query=None):
    out = {}
    async for d in db.collection_items.find({"user_id": uid, **(query or {})}, {"card_id": 1, "variant": 1, "quantity": 1}):
        out.setdefault(d["card_id"], {})[d["variant"]] = d["quantity"]
    return out


# ---------- meta / cards ----------
@api.get("/")
async def root():
    return {"app": "PokeBinder", "ok": True}


@api.get("/meta")
async def meta(user: User = Depends(get_current_user)):
    types, rarities, sets = await asyncio.gather(tcgdex.fetch(db, "/types"), tcgdex.fetch(db, "/rarities"), tcgdex.all_sets(db))
    return {"types": types or [], "rarities": [r for r in (rarities or []) if r != "None"],
            "sets": [{"id": s["id"], "name": s["name"]} for s in reversed(sets)]}


@api.get("/cards")
async def search_cards(q: Optional[str] = None, set_id: Optional[str] = None, type: Optional[str] = None,
                       rarity: Optional[str] = None, category: Optional[str] = None, dex: Optional[int] = None,
                       illustrator: Optional[str] = None, exact: bool = False, sort: Optional[str] = None,
                       page: int = 1, size: int = 36, user: User = Depends(get_current_user)):
    size = max(1, min(size, 250))
    params = {"pagination:page": page, "pagination:itemsPerPage": size}
    if q:
        params["name"] = f"eq:{q}" if exact else q
    if set_id:
        params["set.id"] = f"eq:{set_id}"
    if type:
        params["types"] = type
    if rarity:
        params["rarity"] = f"eq:{rarity}"
    if category:
        params["category"] = category
    if dex:
        params["dexId"] = f"eq:{dex}"
    if illustrator:
        params["illustrator"] = illustrator
    if sort:
        params["sort:field"] = sort.lstrip("-")
        params["sort:order"] = "DESC" if sort.startswith("-") else "ASC"
    items = await tcgdex.fetch(db, "/cards", params, ttl=6 * 3600) or []
    owned = await owned_map(user.id, {"card_id": {"$in": [c["id"] for c in items]}})
    for c in items:
        c["owned"] = sum(owned.get(c["id"], {}).values())
    return {"items": items, "page": page, "has_more": len(items) == size}


@api.get("/cards/{card_id}")
async def card_detail(card_id: str, user: User = Depends(get_current_user)):
    card = await tcgdex.get_card(db, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    owned = (await owned_map(user.id, {"card_id": card_id})).get(card_id, {})
    vs = tcgdex.variants_of(card)
    vs += [v for v in owned if v not in vs]
    variants = []
    for v in vs:
        price = tcgdex.price_for(card, v)
        variants.append({"type": v, "label": tcgdex.VARIANT_LABELS.get(v, v), **price, "owned": owned.get(v, 0)})
        await db.collection_items.update_many({"card_id": card_id, "variant": v}, {"$set": price})
    wish = await db.wishlist.find_one({"user_id": user.id, "card_id": card_id})
    return {"card": card, "variants": variants, "wishlisted": bool(wish)}


# ---------- sets ----------
@api.get("/sets")
async def list_sets(user: User = Depends(get_current_user)):
    series = await tcgdex.fetch(db, "/series", ttl=12 * 3600) or []
    full = await asyncio.gather(*[tcgdex.fetch(db, f"/series/{s['id']}", ttl=12 * 3600) for s in series], return_exceptions=True)
    groups = []
    for s in full:
        if isinstance(s, dict):
            groups.append({"id": s["id"], "name": s["name"], "logo": s.get("logo"), "releaseDate": s.get("releaseDate"),
                           "sets": list(reversed(s.get("sets") or []))})
    groups.sort(key=lambda g: g.get("releaseDate") or "", reverse=True)
    counts = {}
    async for d in db.collection_items.aggregate([{"$match": {"user_id": user.id}},
                                                  {"$group": {"_id": {"s": "$set_id", "c": "$card_id"}}},
                                                  {"$group": {"_id": "$_id.s", "n": {"$sum": 1}}}]):
        counts[d["_id"]] = d["n"]
    goals = [g["set_id"] async for g in db.goals.find({"user_id": user.id})]
    return {"series": groups, "owned_counts": counts, "goals": goals}


@api.get("/sets/{set_id}")
async def set_detail(set_id: str, user: User = Depends(get_current_user)):
    sd = await tcgdex.get_set(db, set_id)
    if not sd:
        raise HTTPException(404, "Set not found")
    owned = await owned_map(user.id, {"set_id": set_id})
    goal = await db.goals.find_one({"user_id": user.id, "set_id": set_id})
    return {"set": sd, "owned": owned, "goal": goal["target"] if goal else None, "progress": tcgdex.progress(sd, owned)}


@api.get("/sets/{set_id}/details")
async def set_card_details(set_id: str, user: User = Depends(get_current_user)):
    sd = await tcgdex.get_set(db, set_id)
    if not sd:
        raise HTTPException(404, "Set not found")
    cards = await asyncio.gather(*[tcgdex.get_card(db, c["id"], ttl=24 * 3600) for c in sd.get("cards", [])], return_exceptions=True)
    out = {}
    for c in cards:
        if isinstance(c, dict):
            vs = tcgdex.variants_of(c)
            out[c["id"]] = {"rarity": c.get("rarity"), "variants": vs, "types": c.get("types") or [], **tcgdex.price_for(c, vs[0])}
    return out


# ---------- goals ----------
class GoalIn(BaseModel):
    set_id: str
    target: str = "base"


async def goals_with_progress(uid):
    out = []
    async for g in db.goals.find({"user_id": uid}).sort("created_at", -1):
        sd = await tcgdex.get_set(db, g["set_id"])
        if not sd:
            continue
        owned = await owned_map(uid, {"set_id": g["set_id"]})
        out.append({"set_id": g["set_id"], "target": g["target"], "name": sd.get("name"), "logo": sd.get("logo"),
                    "symbol": sd.get("symbol"), "serie": (sd.get("serie") or {}).get("name"),
                    "releaseDate": sd.get("releaseDate"), "progress": tcgdex.progress(sd, owned)})
    return out


@api.get("/goals")
async def list_goals(user: User = Depends(get_current_user)):
    return await goals_with_progress(user.id)


@api.post("/goals")
async def set_goal(body: GoalIn, user: User = Depends(get_current_user)):
    if body.target not in ("base", "full", "master"):
        raise HTTPException(400, "Invalid target")
    await db.goals.update_one({"user_id": user.id, "set_id": body.set_id},
                              {"$set": {"target": body.target}, "$setOnInsert": {"created_at": now()}}, upsert=True)
    return {"ok": True}


@api.delete("/goals/{set_id}")
async def delete_goal(set_id: str, user: User = Depends(get_current_user)):
    await db.goals.delete_one({"user_id": user.id, "set_id": set_id})
    return {"ok": True}


# ---------- collection ----------
class AddIn(BaseModel):
    card_id: str
    variant: str = "normal"
    quantity: int = 1


class BatchIn(BaseModel):
    items: List[AddIn]


class QtyIn(BaseModel):
    card_id: str
    variant: str
    quantity: int


class ItemPatch(BaseModel):
    quantity: Optional[int] = None
    condition: Optional[str] = None


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


@api.post("/collection/add")
async def collection_add(body: AddIn, user: User = Depends(get_current_user)):
    name = await add_item(user.id, body.card_id, body.variant, max(1, body.quantity))
    return {"ok": True, "name": name}


@api.post("/collection/batch")
async def collection_batch(body: BatchIn, user: User = Depends(get_current_user)):
    added, failed = 0, []
    for it in body.items:
        try:
            await add_item(user.id, it.card_id, it.variant, max(1, it.quantity))
            added += it.quantity
        except HTTPException:
            failed.append(it.card_id)
    return {"added": added, "failed": failed}


@api.post("/collection/set-qty")
async def collection_set_qty(body: QtyIn, user: User = Depends(get_current_user)):
    flt = {"user_id": user.id, "card_id": body.card_id, "variant": body.variant}
    if body.quantity <= 0:
        await db.collection_items.delete_one(flt)
        return {"ok": True, "quantity": 0}
    if not await db.collection_items.find_one(flt):
        await add_item(user.id, body.card_id, body.variant, body.quantity)
    else:
        await db.collection_items.update_one(flt, {"$set": {"quantity": body.quantity, "updated_at": now()}})
    return {"ok": True, "quantity": body.quantity}


@api.get("/collection")
async def collection_list(q: Optional[str] = None, set_id: Optional[str] = None, variant: Optional[str] = None,
                          sort: str = "recent", user: User = Depends(get_current_user)):
    flt = {"user_id": user.id}
    if q:
        flt["name"] = {"$regex": q, "$options": "i"}
    if set_id:
        flt["set_id"] = set_id
    if variant:
        flt["variant"] = variant
    order = {"recent": [("created_at", -1)], "value": [("price_usd", -1)], "name": [("name", 1)],
             "set": [("set_id", 1), ("local_num", 1)]}.get(sort, [("created_at", -1)])
    docs = await db.collection_items.find(flt).sort(order).to_list(5000)
    return [CollectionItem.from_mongo(d).model_dump() for d in docs]


@api.patch("/collection/{item_id}")
async def collection_patch(item_id: str, body: ItemPatch, user: User = Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nothing to update")
    res = await db.collection_items.update_one({"_id": ObjectId(item_id), "user_id": user.id}, {"$set": {**upd, "updated_at": now()}})
    if not res.matched_count:
        raise HTTPException(404, "Item not found")
    return {"ok": True}


@api.delete("/collection/{item_id}")
async def collection_delete(item_id: str, user: User = Depends(get_current_user)):
    await db.collection_items.delete_one({"_id": ObjectId(item_id), "user_id": user.id})
    return {"ok": True}


async def collection_stats(uid):
    agg = await db.collection_items.aggregate([{"$match": {"user_id": uid}}, {"$group": {
        "_id": None, "qty": {"$sum": "$quantity"}, "unique": {"$addToSet": "$card_id"}, "sets": {"$addToSet": "$set_id"},
        "usd": {"$sum": {"$multiply": [{"$ifNull": ["$price_usd", 0]}, "$quantity"]}},
        "eur": {"$sum": {"$multiply": [{"$ifNull": ["$price_eur", 0]}, "$quantity"]}}}}]).to_list(1)
    a = agg[0] if agg else {}
    return {"total_cards": a.get("qty", 0), "unique_cards": len(a.get("unique", [])), "sets_started": len(a.get("sets", [])),
            "value_usd": round(a.get("usd", 0), 2), "value_eur": round(a.get("eur", 0), 2)}


@api.get("/collection/stats")
async def stats(user: User = Depends(get_current_user)):
    return await collection_stats(user.id)


@api.get("/collection/export")
async def export_csv(user: User = Depends(get_current_user)):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["card_id", "name", "set", "number", "rarity", "variant", "quantity", "condition", "price_usd", "price_eur"])
    async for d in db.collection_items.find({"user_id": user.id}).sort([("set_id", 1), ("local_num", 1)]):
        w.writerow([d["card_id"], d["name"], d.get("set_name"), d.get("local_id"), d.get("rarity"), d["variant"],
                    d["quantity"], d.get("condition"), d.get("price_usd"), d.get("price_eur")])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=collection.csv"})


async def _refresh_prices(uid):
    ids = await db.collection_items.distinct("card_id", {"user_id": uid})
    for cid in ids:
        try:
            card = await tcgdex.get_card(db, cid, ttl=3600)
            async for d in db.collection_items.find({"user_id": uid, "card_id": cid}):
                await db.collection_items.update_one({"_id": d["_id"]}, {"$set": tcgdex.price_for(card, d["variant"])})
        except Exception as e:  # noqa
            logging.warning("price refresh %s failed: %s", cid, e)


@api.post("/collection/refresh-prices")
async def refresh_prices(bg: BackgroundTasks, user: User = Depends(get_current_user)):
    bg.add_task(_refresh_prices, user.id)
    return {"ok": True}


# ---------- wishlist ----------
@api.get("/wishlist")
async def wishlist(user: User = Depends(get_current_user)):
    docs = await db.wishlist.find({"user_id": user.id}, {"_id": 0, "user_id": 0}).sort("added_at", -1).to_list(2000)
    owned = await owned_map(user.id, {"card_id": {"$in": [d["card_id"] for d in docs]}})
    for d in docs:
        d["owned"] = sum(owned.get(d["card_id"], {}).values())
    return docs


@api.post("/wishlist/{card_id}")
async def wishlist_toggle(card_id: str, user: User = Depends(get_current_user)):
    flt = {"user_id": user.id, "card_id": card_id}
    if await db.wishlist.find_one(flt):
        await db.wishlist.delete_one(flt)
        return {"wishlisted": False}
    card = await tcgdex.get_card(db, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    s = tcgdex.summarize(card)
    await db.wishlist.insert_one({**flt, "name": s["name"], "image": s["image"], "set_name": s["set_name"],
                                  "local_id": s["local_id"], **tcgdex.price_for(card, tcgdex.variants_of(card)[0]),
                                  "added_at": now()})
    return {"wishlisted": True}


# ---------- pokedex ----------
@api.get("/pokedex")
async def pokedex(user: User = Depends(get_current_user)):
    data = await tcgdex.fetch_url(db, f"{tcgdex.POKEAPI}/pokemon-species", {"limit": 2000}, ttl=7 * 24 * 3600) or {}
    out = []
    for r in data.get("results", []):
        pid = int(r["url"].rstrip("/").split("/")[-1])
        out.append({"id": pid, "name": r["name"]})
    return sorted(out, key=lambda x: x["id"])


# ---------- dashboard ----------
@api.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    st = await collection_stats(user.id)
    recent = await db.collection_items.find({"user_id": user.id}).sort("created_at", -1).to_list(12)
    top = await db.collection_items.find({"user_id": user.id, "price_usd": {"$ne": None}}).sort("price_usd", -1).to_list(6)
    goals = await goals_with_progress(user.id)
    ser = lambda ds: [CollectionItem.from_mongo(d).model_dump() for d in ds]  # noqa: E731
    return {"stats": st, "recent": ser(recent), "top": ser(top), "goals": goals[:6]}


# ---------- scanner ----------
class IndexIn(BaseModel):
    set_ids: Optional[List[str]] = None
    goals_only: bool = False


@api.post("/scan")
async def scan(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Image too large")
    return await scanner.recognize(db, data)


@api.get("/scan/index/status")
async def index_status(user: User = Depends(get_current_user)):
    return scanner.index_status()


@api.post("/scan/index")
async def index_build(body: IndexIn, user: User = Depends(get_current_user)):
    if scanner.status["running"]:
        raise HTTPException(409, "Indexing already running")
    ids = body.set_ids
    if body.goals_only:
        ids = [g["set_id"] async for g in db.goals.find({"user_id": user.id})]
        if not ids:
            raise HTTPException(400, "Track some sets first")
    asyncio.create_task(scanner.build_index(db, ids))
    return {"ok": True}


app.include_router(auth_router)
app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=False, allow_origins=os.environ["CORS_ORIGINS"].split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await seed_admin()
    await db.collection_items.create_index([("user_id", 1), ("card_id", 1), ("variant", 1)], unique=True)
    await db.collection_items.create_index([("user_id", 1), ("set_id", 1)])
    await db.goals.create_index([("user_id", 1), ("set_id", 1)], unique=True)
    await db.wishlist.create_index([("user_id", 1), ("card_id", 1)], unique=True)
    asyncio.create_task(scanner.load_index(db))


@app.on_event("shutdown")
async def shutdown():
    client.close()
