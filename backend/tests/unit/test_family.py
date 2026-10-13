async def _setup(c, make_user):
    a, b = await make_user("Kid"), await make_user("Dad")
    await c.post("/api/collection/add", json={"card_id": "tst1-2", "variant": "normal", "quantity": 3}, headers=a["headers"])
    await c.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "normal", "quantity": 1}, headers=a["headers"])
    await c.post("/api/collection/add", json={"card_id": "tst2-1", "variant": "normal", "quantity": 2}, headers=b["headers"])
    await c.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "normal", "quantity": 1}, headers=b["headers"])
    await c.post("/api/goals", json={"set_id": "tst1"}, headers=b["headers"])
    return a, b


async def test_members_excludes_self(app_client, make_user):
    a, b = await _setup(app_client, make_user)
    m = (await app_client.get("/api/family/members", headers=a["headers"])).json()
    ids = [x["id"] for x in m]
    assert b["user"]["id"] in ids and a["user"]["id"] not in ids


async def test_compare_finds_duplicates_and_goal_needs(app_client, make_user):
    a, b = await _setup(app_client, make_user)
    d = (await app_client.get(f"/api/family/compare/{b['user']['id']}", headers=a["headers"])).json()
    assert d["counts"] == {"shared": 1, "only_me": 1, "only_them": 1}
    give = d["i_can_give"]
    assert [c["card_id"] for c in give] == ["tst1-2"]
    assert give[0]["needed_for_goal"] is True and give[0]["spare_qty"] == 2 and give[0]["spare_variant"] == "normal"
    assert [c["card_id"] for c in d["they_can_give"]] == ["tst2-1"]
    assert d["they_can_give"][0]["needed_for_goal"] is False


async def test_compare_errors(app_client, make_user):
    a = await make_user()
    assert (await app_client.get(f"/api/family/compare/{a['user']['id']}", headers=a["headers"])).status_code == 404
    assert (await app_client.get("/api/family/compare/notanid", headers=a["headers"])).status_code == 404


async def test_give_moves_a_copy_and_logs(app_client, make_user):
    a, b = await _setup(app_client, make_user)
    body = {"to_user_id": b["user"]["id"], "card_id": "tst1-2", "variant": "normal"}
    assert (await app_client.post("/api/family/give", json=body, headers=a["headers"])).status_code == 200
    mine = {i["card_id"]: i["quantity"] for i in (await app_client.get("/api/collection", headers=a["headers"])).json()}
    theirs = {i["card_id"]: i["quantity"] for i in (await app_client.get("/api/collection", headers=b["headers"])).json()}
    assert mine["tst1-2"] == 2 and theirs["tst1-2"] == 1
    log = (await app_client.get("/api/family/activity", headers=b["headers"])).json()
    assert log[0]["from_name"] == "Kid" and log[0]["to_name"] == "Dad" and log[0]["card_id"] == "tst1-2"


async def test_give_last_copy_removes_item(app_client, make_user):
    a, b = await _setup(app_client, make_user)
    body = {"to_user_id": b["user"]["id"], "card_id": "tst1-1", "variant": "normal"}
    assert (await app_client.post("/api/family/give", json=body, headers=a["headers"])).status_code == 200
    ids = [i["card_id"] for i in (await app_client.get("/api/collection", headers=a["headers"])).json()]
    assert "tst1-1" not in ids


async def test_give_validation(app_client, make_user):
    a, b = await _setup(app_client, make_user)
    h = a["headers"]
    to = b["user"]["id"]
    assert (await app_client.post("/api/family/give", json={"to_user_id": to, "card_id": "tst1-2", "variant": "normal", "quantity": 10}, headers=h)).status_code == 400
    assert (await app_client.post("/api/family/give", json={"to_user_id": to, "card_id": "tst1-3", "variant": "holo"}, headers=h)).status_code == 400
    assert (await app_client.post("/api/family/give", json={"to_user_id": a["user"]["id"], "card_id": "tst1-2", "variant": "normal"}, headers=h)).status_code == 400
    assert (await app_client.post("/api/family/give", json={"to_user_id": "64b000000000000000000000", "card_id": "tst1-2", "variant": "normal"}, headers=h)).status_code == 404
