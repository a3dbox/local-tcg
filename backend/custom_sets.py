from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import tcgdex
from auth import get_current_user
from database import db
from models import User
from ops import now, owned_map

router = APIRouter(prefix="/api/custom-sets")
RULE_KEYS = ("q", "exact", "type", "rarity", "category", "dex", "set_id", "illustrator")


class Rules(BaseModel):
    q: Optional[str] = None
    exact: bool = False
    type: Optional[str] = None
    rarity: Optional[str] = None
    category: Optional[str] = None
    dex: Optional[int] = None
    set_id: Optional[str] = None
    illustrator: Optional[str] = None


class CustomSetIn(BaseModel):
    name: str
    description: str = ""
    rules: Rules = Rules()
    card_ids: List[str] = []


class CustomSetPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[Rules] = None


class CardIn(BaseModel):
    card_id: str


def has_rules(rules: dict) -> bool:
    return any(v for k, v in (rules or {}).items() if k != "exact")


async def _get(uid, cs_id):
    d = await db.custom_sets.find_one({"_id": ObjectId(cs_id), "user_id": uid}) if ObjectId.is_valid(cs_id) else None
    if not d:
        raise HTTPException(404, "Custom set not found")
    return d


async def resolve_cards(cs) -> list:
    cards = {}
    rules = cs.get("rules") or {}
    if has_rules(rules):
        params = tcgdex.search_params(**{k: rules.get(k) for k in RULE_KEYS})
        for page in range(1, 9):
            res = await tcgdex.fetch(db, "/cards", {**params, "pagination:page": page, "pagination:itemsPerPage": 250}, ttl=6 * 3600) or []
            for c in res:
                cards[c["id"]] = c
            if len(res) < 250:
                break
    for cid in cs.get("card_ids") or []:
        if cid not in cards:
            full = await tcgdex.get_card(db, cid)
            if full:
                cards[cid] = {k: full.get(k) for k in ("id", "localId", "name", "image")}
    excluded = set(cs.get("excluded_ids") or [])
    names = {s["id"]: s["name"] for s in await tcgdex.all_sets(db)}
    out = []
    for c in cards.values():
        if c["id"] in excluded:
            continue
        sid = c["id"].rsplit("-", 1)[0]
        out.append({**c, "set_id": sid, "set_name": names.get(sid)})
    return out


def _summary(d, cards, owned):
    have = sum(1 for c in cards if c["id"] in owned)
    return {"id": str(d["_id"]), "name": d["name"], "description": d.get("description", ""), "rules": d.get("rules") or {},
            "card_ids": d.get("card_ids") or [], "progress": [have, len(cards)],
            "cover": next((c["image"] for c in cards if c.get("image")), None), "created_at": d.get("created_at")}


@router.get("")
async def list_custom_sets(user: User = Depends(get_current_user)):
    owned = await owned_map(user.id)
    out = []
    async for d in db.custom_sets.find({"user_id": user.id}).sort("created_at", -1):
        out.append(_summary(d, await resolve_cards(d), owned))
    return out


@router.post("")
async def create_custom_set(body: CustomSetIn, user: User = Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(400, "Please enter a name")
    rules = body.rules.model_dump()
    if not has_rules(rules) and not body.card_ids:
        rules = {}
    doc = {"user_id": user.id, "name": body.name.strip(), "description": body.description, "rules": rules,
           "card_ids": list(dict.fromkeys(body.card_ids)), "excluded_ids": [], "created_at": now()}
    res = await db.custom_sets.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _summary(doc, await resolve_cards(doc), await owned_map(user.id))


@router.get("/{cs_id}")
async def custom_set_detail(cs_id: str, user: User = Depends(get_current_user)):
    d = await _get(user.id, cs_id)
    cards = await resolve_cards(d)
    owned = await owned_map(user.id, {"card_id": {"$in": [c["id"] for c in cards]}})
    return {**_summary(d, cards, owned), "cards": cards, "owned": owned, "excluded_ids": d.get("excluded_ids") or []}


@router.patch("/{cs_id}")
async def update_custom_set(cs_id: str, body: CustomSetPatch, user: User = Depends(get_current_user)):
    await _get(user.id, cs_id)
    upd = {}
    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(400, "Please enter a name")
        upd["name"] = body.name.strip()
    if body.description is not None:
        upd["description"] = body.description
    if body.rules is not None:
        upd["rules"] = body.rules.model_dump()
    if upd:
        await db.custom_sets.update_one({"_id": ObjectId(cs_id)}, {"$set": upd})
    return await custom_set_detail(cs_id, user)


@router.delete("/{cs_id}")
async def delete_custom_set(cs_id: str, user: User = Depends(get_current_user)):
    await _get(user.id, cs_id)
    await db.custom_sets.delete_one({"_id": ObjectId(cs_id)})
    return {"ok": True}


@router.post("/{cs_id}/cards")
async def add_card(cs_id: str, body: CardIn, user: User = Depends(get_current_user)):
    await _get(user.id, cs_id)
    if not await tcgdex.get_card(db, body.card_id):
        raise HTTPException(404, "Card not found")
    await db.custom_sets.update_one({"_id": ObjectId(cs_id)}, {"$addToSet": {"card_ids": body.card_id},
                                                               "$pull": {"excluded_ids": body.card_id}})
    return {"ok": True}


@router.delete("/{cs_id}/cards/{card_id}")
async def remove_card(cs_id: str, card_id: str, user: User = Depends(get_current_user)):
    d = await _get(user.id, cs_id)
    upd = {"$pull": {"card_ids": card_id}}
    if has_rules(d.get("rules")):
        upd["$addToSet"] = {"excluded_ids": card_id}
    await db.custom_sets.update_one({"_id": d["_id"]}, upd)
    return {"ok": True}
