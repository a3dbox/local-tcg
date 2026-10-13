import uuid


async def test_register_login_me_refresh(app_client, make_user):
    u = await make_user("Ash")
    r = await app_client.get("/api/auth/me", headers=u["headers"])
    assert r.status_code == 200 and r.json()["name"] == "Ash" and "password_hash" not in r.json()
    r = await app_client.post("/api/auth/login", json={"email": u["email"].upper(), "password": u["password"]})
    assert r.status_code == 200 and r.json()["user"]["email"] == u["email"]
    r = await app_client.post("/api/auth/refresh", json={"refresh_token": u["refresh"]})
    assert r.status_code == 200 and r.json()["access_token"]


async def test_password_is_bcrypt_hashed(make_user, db):
    u = await make_user("Hash")
    doc = await db.users.find_one({"email": u["email"]})
    assert doc["password_hash"].startswith("$2b$") and doc["role"] == "user"


async def test_register_validation(app_client, make_user):
    u = await make_user("Dup")
    bad = [{"name": "x", "email": u["email"], "password": "secret12"},
           {"name": "x", "email": "not-an-email", "password": "secret12"},
           {"name": "x", "email": f"{uuid.uuid4().hex}@t.io", "password": "123"},
           {"name": " ", "email": f"{uuid.uuid4().hex}@t.io", "password": "secret12"}]
    for body in bad:
        assert (await app_client.post("/api/auth/register", json=body)).status_code == 400


async def test_wrong_password_and_lockout(app_client, make_user):
    u = await make_user("Lock")
    for _ in range(5):
        r = await app_client.post("/api/auth/login", json={"email": u["email"], "password": "wrong"})
        assert r.status_code == 401
    r = await app_client.post("/api/auth/login", json={"email": u["email"], "password": u["password"]})
    assert r.status_code == 429


async def test_protected_routes_need_valid_access_token(app_client, make_user):
    assert (await app_client.get("/api/collection")).status_code == 401
    assert (await app_client.get("/api/collection", headers={"Authorization": "Bearer junk"})).status_code == 401
    u = await make_user("Tok")
    r = await app_client.get("/api/collection", headers={"Authorization": f"Bearer {u['refresh']}"})
    assert r.status_code == 401


async def test_refresh_rejects_bad_token(app_client):
    assert (await app_client.post("/api/auth/refresh", json={"refresh_token": "nope"})).status_code == 401
    assert (await app_client.post("/api/auth/refresh", json={})).status_code == 401


async def test_forgot_and_reset_password(app_client, make_user, db):
    u = await make_user("Reset")
    assert (await app_client.post("/api/auth/forgot-password", json={"email": u["email"]})).status_code == 200
    tok = (await db.password_reset_tokens.find_one({"user_id": u["user"]["id"]}))["token"]
    r = await app_client.post("/api/auth/reset-password", json={"token": tok, "password": "brandnew1"})
    assert r.status_code == 200
    assert (await app_client.post("/api/auth/reset-password", json={"token": tok, "password": "again123"})).status_code == 400
    r = await app_client.post("/api/auth/login", json={"email": u["email"], "password": "brandnew1"})
    assert r.status_code == 200


async def test_admin_is_seeded(admin):
    assert admin["user"]["role"] == "admin"
