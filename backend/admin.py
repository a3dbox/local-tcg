from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, hash_password
from database import db
from models import User
from ops import collection_stats

router = APIRouter(prefix="/api/admin")
ROLES = ("user", "admin")


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admins only")
    return user


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"


class UserPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


def _check(email=None, password=None, role=None, name=None):
    if email is not None and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(400, "Please enter a valid email")
    if password is not None and len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if role is not None and role not in ROLES:
        raise HTTPException(400, "Invalid role")
    if name is not None and not name.strip():
        raise HTTPException(400, "Please enter a name")


async def _get(user_id):
    doc = await db.users.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) else None
    if not doc:
        raise HTTPException(404, "User not found")
    return User.from_mongo(doc)


@router.get("/users")
async def list_users(admin: User = Depends(require_admin)):
    out = []
    async for d in db.users.find({}).sort("created_at", 1):
        u = User.from_mongo(d)
        out.append({**u.public(), **await collection_stats(u.id), "is_self": u.id == admin.id})
    return out


@router.post("/users")
async def create_user(body: UserCreate, admin: User = Depends(require_admin)):
    email = body.email.strip().lower()
    _check(email, body.password, body.role, body.name)
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    u = User(email=email, name=body.name.strip(), role=body.role, password_hash=hash_password(body.password),
             created_at=datetime.now(timezone.utc).isoformat())
    res = await db.users.insert_one(u.to_mongo())
    u.id = str(res.inserted_id)
    return u.public()


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: UserPatch, admin: User = Depends(require_admin)):
    u = await _get(user_id)
    email = body.email.strip().lower() if body.email is not None else None
    _check(email, body.password, body.role, body.name)
    upd = {}
    if body.name is not None:
        upd["name"] = body.name.strip()
    if email is not None and email != u.email:
        if await db.users.find_one({"email": email}):
            raise HTTPException(400, "Email already registered")
        upd["email"] = email
    if body.role is not None and body.role != u.role:
        if u.id == admin.id:
            raise HTTPException(400, "You can't change your own role")
        upd["role"] = body.role
    if body.password:
        upd["password_hash"] = hash_password(body.password)
    if not upd:
        raise HTTPException(400, "Nothing to update")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": upd})
    return (await _get(user_id)).public()


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    u = await _get(user_id)
    if u.id == admin.id:
        raise HTTPException(400, "You can't delete your own account")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    for coll in (db.collection_items, db.goals, db.wishlist, db.value_history, db.locations, db.custom_sets):
        await coll.delete_many({"user_id": user_id})
    return {"ok": True}
