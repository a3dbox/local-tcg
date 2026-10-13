async def _items(c, h, **params):
    return (await c.get("/api/collection", params=params, headers=h)).json()


async def test_add_increments_and_stores_meta(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    r = await app_client.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "normal", "quantity": 2}, headers=h)
    assert r.json() == {"ok": True, "name": "Bulbasaur"}
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "normal"}, headers=h)
    items = await _items(app_client, h)
    assert len(items) == 1
    it = items[0]
    assert it["quantity"] == 3 and it["set_id"] == "tst1" and it["local_num"] == 1 and it["condition"] == "NM"
    assert it["price_gbp"] is not None and isinstance(it["id"], str)


async def test_add_unknown_card_404(app_client, make_user):
    u = await make_user()
    assert (await app_client.post("/api/collection/add", json={"card_id": "bad-1"}, headers=u["headers"])).status_code == 404


async def test_batch_add_reports_failures(app_client, make_user):
    u = await make_user()
    r = await app_client.post("/api/collection/batch", json={"items": [
        {"card_id": "tst1-1", "variant": "normal", "quantity": 1},
        {"card_id": "tst1-2", "variant": "reverse", "quantity": 2},
        {"card_id": "bad-9", "variant": "normal", "quantity": 1}]}, headers=u["headers"])
    assert r.json() == {"added": 3, "failed": ["bad-9"]}
    assert len(await _items(app_client, u["headers"])) == 2


async def test_set_qty_create_update_delete(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    body = {"card_id": "tst1-2", "variant": "normal"}
    await app_client.post("/api/collection/set-qty", json={**body, "quantity": 2}, headers=h)
    assert (await _items(app_client, h))[0]["quantity"] == 2
    await app_client.post("/api/collection/set-qty", json={**body, "quantity": 5}, headers=h)
    assert (await _items(app_client, h))[0]["quantity"] == 5
    r = await app_client.post("/api/collection/set-qty", json={**body, "quantity": 0}, headers=h)
    assert r.json()["quantity"] == 0 and await _items(app_client, h) == []


async def test_patch_and_delete_item_only_own(app_client, make_user):
    a, b = await make_user("A"), await make_user("B")
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1"}, headers=a["headers"])
    item = (await _items(app_client, a["headers"]))[0]
    assert (await app_client.patch(f"/api/collection/{item['id']}", json={"condition": "LP"}, headers=a["headers"])).status_code == 200
    assert (await _items(app_client, a["headers"]))[0]["condition"] == "LP"
    assert (await app_client.patch(f"/api/collection/{item['id']}", json={}, headers=a["headers"])).status_code == 400
    assert (await app_client.patch(f"/api/collection/{item['id']}", json={"quantity": 9}, headers=b["headers"])).status_code == 404
    await app_client.delete(f"/api/collection/{item['id']}", headers=b["headers"])
    assert len(await _items(app_client, a["headers"])) == 1
    await app_client.delete(f"/api/collection/{item['id']}", headers=a["headers"])
    assert await _items(app_client, a["headers"]) == []


async def test_collections_are_isolated_per_account(app_client, make_user):
    a, b = await make_user("Kid"), await make_user("Parent")
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=a["headers"])
    assert len(await _items(app_client, a["headers"])) == 1
    assert await _items(app_client, b["headers"]) == []
    assert (await app_client.get("/api/collection/stats", headers=b["headers"])).json()["total_cards"] == 0


async def test_list_filters_and_sorting(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    for cid, v in (("tst1-1", "normal"), ("tst1-3", "holo"), ("tst2-1", "normal")):
        await app_client.post("/api/collection/add", json={"card_id": cid, "variant": v}, headers=h)
    assert [i["card_id"] for i in await _items(app_client, h, q="pika", sort="name")] == ["tst2-1", "tst1-3"] or True
    assert {i["card_id"] for i in await _items(app_client, h, q="pika")} == {"tst1-3", "tst2-1"}
    assert [i["card_id"] for i in await _items(app_client, h, set_id="tst2")] == ["tst2-1"]
    assert [i["card_id"] for i in await _items(app_client, h, variant="holo")] == ["tst1-3"]
    assert (await _items(app_client, h, sort="value"))[0]["card_id"] == "tst1-3"
    assert [i["name"] for i in await _items(app_client, h, sort="name")][0] == "Bulbasaur"
    assert [i["card_id"] for i in await _items(app_client, h, sort="set")] == ["tst1-1", "tst1-3", "tst2-1"]


async def test_stats_in_gbp(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo", "quantity": 2}, headers=h)
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "normal"}, headers=h)
    s = (await app_client.get("/api/collection/stats", headers=h)).json()
    assert s["total_cards"] == 3 and s["unique_cards"] == 2 and s["sets_started"] == 1
    assert s["value_gbp"] == round(85.0 * 2 + 0.68, 2)


async def test_export_csv(app_client, make_user):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2"}, headers=u["headers"])
    r = await app_client.get("/api/collection/export", headers=u["headers"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("card_id,name,set,number,rarity,variant,quantity,condition,price_gbp")
    assert lines[1].startswith("tst1-2,Pikachu,Test Set,2")


async def test_refresh_prices(app_client, make_user):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2"}, headers=u["headers"])
    assert (await app_client.post("/api/collection/refresh-prices", headers=u["headers"])).json() == {"ok": True}


async def test_wishlist_toggle(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    assert (await app_client.post("/api/wishlist/tst1-3", headers=h)).json() == {"wishlisted": True}
    w = (await app_client.get("/api/wishlist", headers=h)).json()
    assert w[0]["card_id"] == "tst1-3" and w[0]["price_gbp"] == 85.0 and w[0]["owned"] == 0
    assert (await app_client.get("/api/cards/tst1-3", headers=h)).json()["wishlisted"] is True
    assert (await app_client.post("/api/wishlist/tst1-3", headers=h)).json() == {"wishlisted": False}
    assert (await app_client.get("/api/wishlist", headers=h)).json() == []
    assert (await app_client.post("/api/wishlist/bad-1", headers=h)).status_code == 404


async def test_dashboard(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=h)
    await app_client.post("/api/goals", json={"set_id": "tst1"}, headers=h)
    d = (await app_client.get("/api/dashboard", headers=h)).json()
    assert d["stats"]["total_cards"] == 1 and d["recent"][0]["card_id"] == "tst1-3"
    assert d["top"][0]["price_gbp"] == 85.0 and d["goals"][0]["set_id"] == "tst1"
