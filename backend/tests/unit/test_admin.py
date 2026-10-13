async def test_non_admin_forbidden(app_client, make_user):
    u = await make_user()
    for method, url in (("get", "/api/admin/users"), ("post", "/api/admin/users"), ("delete", "/api/admin/users/x")):
        r = await getattr(app_client, method)(url, headers=u["headers"], **({"json": {}} if method == "post" else {}))
        assert r.status_code in (403, 422) and (r.status_code == 403 or method == "post")
    r = await app_client.get("/api/admin/users", headers=u["headers"])
    assert r.status_code == 403


async def test_list_users_with_stats(app_client, admin, make_user):
    u = await make_user("Listed")
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=u["headers"])
    users = (await app_client.get("/api/admin/users", headers=admin["headers"])).json()
    me = next(x for x in users if x["id"] == admin["user"]["id"])
    other = next(x for x in users if x["id"] == u["user"]["id"])
    assert me["is_self"] is True and other["is_self"] is False
    assert other["total_cards"] == 1 and other["value_gbp"] == 85.0 and "password_hash" not in other


async def test_create_user_and_login(app_client, admin):
    body = {"name": "Misty", "email": "Misty-admin@test.io", "password": "water123", "role": "user"}
    r = await app_client.post("/api/admin/users", json=body, headers=admin["headers"])
    assert r.status_code == 200 and r.json()["email"] == "misty-admin@test.io"
    assert (await app_client.post("/api/admin/users", json=body, headers=admin["headers"])).status_code == 400
    assert (await app_client.post("/api/admin/users", json={**body, "email": "x@y.io", "role": "boss"}, headers=admin["headers"])).status_code == 400
    assert (await app_client.post("/api/admin/users", json={**body, "email": "z@y.io", "password": "1"}, headers=admin["headers"])).status_code == 400
    assert (await app_client.post("/api/auth/login", json={"email": "misty-admin@test.io", "password": "water123"})).status_code == 200


async def test_update_user_role_name_password(app_client, admin, make_user):
    u = await make_user("Brock")
    uid = u["user"]["id"]
    r = await app_client.patch(f"/api/admin/users/{uid}", json={"name": "Brock Sr", "role": "admin", "password": "rock5678"}, headers=admin["headers"])
    assert r.status_code == 200 and r.json()["name"] == "Brock Sr" and r.json()["role"] == "admin"
    assert (await app_client.post("/api/auth/login", json={"email": u["email"], "password": "rock5678"})).status_code == 200
    assert (await app_client.patch(f"/api/admin/users/{uid}", json={}, headers=admin["headers"])).status_code == 400
    assert (await app_client.patch("/api/admin/users/bad", json={"name": "x"}, headers=admin["headers"])).status_code == 404


async def test_update_email_conflict(app_client, admin, make_user):
    a, b = await make_user("E1"), await make_user("E2")
    r = await app_client.patch(f"/api/admin/users/{a['user']['id']}", json={"email": b["email"]}, headers=admin["headers"])
    assert r.status_code == 400


async def test_admin_cannot_change_own_role_or_delete_self(app_client, admin):
    me = admin["user"]["id"]
    assert (await app_client.patch(f"/api/admin/users/{me}", json={"role": "user"}, headers=admin["headers"])).status_code == 400
    assert (await app_client.delete(f"/api/admin/users/{me}", headers=admin["headers"])).status_code == 400


async def test_delete_user_removes_data(app_client, admin, make_user, db):
    u = await make_user("Gone")
    h = u["headers"]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1"}, headers=h)
    await app_client.post("/api/goals", json={"set_id": "tst1"}, headers=h)
    await app_client.post("/api/wishlist/tst1-2", headers=h)
    assert (await app_client.delete(f"/api/admin/users/{u['user']['id']}", headers=admin["headers"])).status_code == 200
    for coll in (db.collection_items, db.goals, db.wishlist):
        assert await coll.count_documents({"user_id": u["user"]["id"]}) == 0
    assert (await app_client.get("/api/auth/me", headers=h)).status_code == 401
