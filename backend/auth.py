import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import db
from models import User

router = APIRouter(prefix="/api/auth")
ALG = "HS256"
log = logging.getLogger("auth")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())


def _secret():
    return os.environ["JWT_SECRET"]


def make_tokens(user: User) -> dict:
    now = datetime.now(timezone.utc)
    access = jwt.encode({"sub": user.id, "email": user.email, "exp": now + timedelta(minutes=15), "type": "access"}, _secret(), algorithm=ALG)
    refresh = jwt.encode({"sub": user.id, "exp": now + timedelta(days=7), "type": "refresh"}, _secret(), algorithm=ALG)
    return {"user": user.public(), "access_token": access, "refresh_token": refresh}


async def get_current_user(request: Request) -> User:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    token = token or request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(payload["sub"])}))
    if not user:
        raise HTTPException(401, "User not found")
    return user


class RegisterIn(BaseModel):
    email: str
    password: str
    name: str


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: Optional[str] = None


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    password: str


@router.post("/register")
async def register(body: RegisterIn):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Please enter a valid email")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if not body.name.strip():
        raise HTTPException(400, "Please enter a name")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password),
                created_at=datetime.now(timezone.utc).isoformat())
    res = await db.users.insert_one(user.to_mongo())
    user.id = str(res.inserted_id)
    return make_tokens(user)


@router.post("/login")
async def login(body: LoginIn, request: Request):
    email = body.email.strip().lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    now = datetime.now(timezone.utc)
    att = await db.login_attempts.find_one({"identifier": ident})
    window = now - timedelta(minutes=15)
    if att and att["count"] >= 5 and att["last"] > window:
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user = User.from_mongo(await db.users.find_one({"email": email}))
    if not user or not verify_password(body.password, user.password_hash or ""):
        if att and att["last"] > window:
            await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last": now}})
        else:
            await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": 1, "last": now}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_many({"identifier": ident})
    return make_tokens(user)


@router.post("/refresh")
async def refresh(body: RefreshIn, request: Request):
    token = body.refresh_token or request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(payload["sub"])}))
    if not user:
        raise HTTPException(401, "User not found")
    return make_tokens(user)


@router.get("/me")
async def me(request: Request):
    return (await get_current_user(request)).public()


@router.post("/logout")
async def logout():
    return {"ok": True}


@router.post("/forgot-password")
async def forgot(body: ForgotIn):
    user = await db.users.find_one({"email": body.email.strip().lower()})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"token": token, "user_id": str(user["_id"]), "used": False,
                                                   "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
        log.warning("Password reset link: /reset-password?token=%s", token)
    return {"ok": True}


@router.post("/reset-password")
async def reset(body: ResetIn):
    doc = await db.password_reset_tokens.find_one({"token": body.token})
    if not doc or doc["used"] or doc["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired token")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    await db.users.update_one({"_id": ObjectId(doc["user_id"])}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})
    return {"ok": True}


async def seed_admin():
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    email, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": email})
    if not existing:
        user = User(email=email, name="Admin", role="admin", password_hash=hash_password(pw),
                    created_at=datetime.now(timezone.utc).isoformat())
        await db.users.insert_one(user.to_mongo())
    elif not verify_password(pw, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
