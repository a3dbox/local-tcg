async def _loc(c, h, name="Red Case", kind="case"):
    r = await c.post("/api/locations", json={"name": name, "kind": kind}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def _item(c, h, card_id="tst1-2", variant="normal", qty=3, location_id=None):
    await c.post("/api/collection/add", json={"card_id": card_id, "variant": variant, "quantity": qty, "location_id": location_id}, headers=h)
    items = (await c.get("/api/collection", headers=h)).json()
    return next(i for i in items if i["card_id"] == card_id and i["variant"] == variant)


async def test_location_crud_and_validation(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    assert (await app_client.post("/api/locations", json={"name": " ", "kind": "box"}, headers=h)).status_code == 400
    assert (await app_client.post("/api/locations", json={"name": "X", "kind": "shoe"}, headers=h)).status_code == 400
    lid = await _loc(app_client, h)
    r = await app_client.patch(f"/api/locations/{lid}", json={"name": "Blue Case", "kind": "binder"}, headers=h)
    assert r.json()["name"] == "Blue Case" and r.json()["kind"] == "binder"
    assert (await app_client.patch(f"/api/locations/{lid}", json={"kind": "nope"}, headers=h)).status_code == 400
    d = (await app_client.get("/api/locations", headers=h)).json()
    assert [x["name"] for x in d["locations"]] == ["Blue Case"]
    other = await make_user("Other")
    assert (await app_client.get(f"/api/locations/{lid}", headers=other["headers"])).status_code == 404
    assert (await app_client.delete(f"/api/locations/{lid}", headers=h)).status_code == 200
    assert (await app_client.get("/api/locations", headers=h)).json()["locations"] == []


async def test_place_move_and_counts(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    case, bulk = await _loc(app_client, h, "Case"), await _loc(app_client, h, "Bulk box", "bulk")
    it = await _item(app_client, h, qty=3)
    assert (await app_client.post(f"/api/locations/{case}/place", json={"item_id": it["id"], "quantity": 2}, headers=h)).status_code == 200
    assert (await app_client.post(f"/api/locations/{bulk}/place", json={"item_id": it["id"], "quantity": 2}, headers=h)).status_code == 400
    r = await app_client.post("/api/locations/move", json={"item_id": it["id"], "from_id": "unassigned", "to_id": bulk, "quantity": 1}, headers=h)
    assert r.json()["placements"] == {case: 2, bulk: 1}
    r = await app_client.post("/api/locations/move", json={"item_id": it["id"], "from_id": case, "to_id": bulk, "quantity": 1}, headers=h)
    assert r.json()["placements"] == {case: 1, bulk: 2}
    assert (await app_client.post("/api/locations/move", json={"item_id": it["id"], "from_id": case, "to_id": bulk, "quantity": 5}, headers=h)).status_code == 400
    d = (await app_client.get(f"/api/locations/{bulk}", headers=h)).json()
    assert d["cards"] == 2 and d["items"][0]["placed"] == 2 and d["location"]["name"] == "Bulk box"
    summary = (await app_client.get("/api/locations", headers=h)).json()
    assert {x["name"]: x["cards"] for x in summary["locations"]} == {"Case": 1, "Bulk box": 2}
    assert summary["unassigned"]["cards"] == 0


async def test_add_directly_into_location_and_unassigned(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    lid = await _loc(app_client, h)
    await _item(app_client, h, "tst1-1", qty=2, location_id=lid)
    await _item(app_client, h, "tst1-3", "holo", qty=1)
    assert (await app_client.get(f"/api/locations/{lid}", headers=h)).json()["cards"] == 2
    un = (await app_client.get("/api/locations/unassigned/items", headers=h)).json()
    assert [i["card_id"] for i in un] == ["tst1-3"] and un[0]["placed"] == 1
    assert [i["card_id"] for i in (await app_client.get("/api/collection", params={"location_id": lid}, headers=h)).json()] == ["tst1-1"]
    assert [i["card_id"] for i in (await app_client.get("/api/collection", params={"location_id": "unassigned"}, headers=h)).json()] == ["tst1-3"]
    r = await app_client.post("/api/collection/add", json={"card_id": "tst1-1", "location_id": "64b000000000000000000000"}, headers=h)
    assert r.status_code == 404


async def test_batch_add_into_location(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    lid = await _loc(app_client, h, "Scan box", "box")
    r = await app_client.post("/api/collection/batch", json={"location_id": lid, "items": [
        {"card_id": "tst1-1", "variant": "normal", "quantity": 1}, {"card_id": "tst1-2", "variant": "normal", "quantity": 2}]}, headers=h)
    assert r.json()["added"] == 3
    assert (await app_client.get(f"/api/locations/{lid}", headers=h)).json()["cards"] == 3


async def test_reducing_quantity_clamps_placements(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    lid = await _loc(app_client, h)
    await _item(app_client, h, qty=4, location_id=lid)
    await app_client.post("/api/collection/set-qty", json={"card_id": "tst1-2", "variant": "normal", "quantity": 1}, headers=h)
    it = (await app_client.get("/api/collection", headers=h)).json()[0]
    assert it["placements"] == {lid: 1}


async def test_deleting_location_unassigns_cards(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    lid = await _loc(app_client, h)
    await _item(app_client, h, qty=2, location_id=lid)
    await app_client.delete(f"/api/locations/{lid}", headers=h)
    it = (await app_client.get("/api/collection", headers=h)).json()[0]
    assert it["placements"] == {} and it["quantity"] == 2


async def test_card_detail_shows_where_copies_are(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    lid = await _loc(app_client, h, "Binder A", "binder")
    await _item(app_client, h, qty=3, location_id=lid)
    await _item(app_client, h, qty=1)
    where = (await app_client.get("/api/cards/tst1-2", headers=h)).json()["where"]
    assert {(w["name"], w["quantity"]) for w in where} == {("Binder A", 3), ("Not stored yet", 1)}


async def test_duplicates_filter_and_card_total(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await _item(app_client, h, "tst1-1", "normal", qty=1)
    await _item(app_client, h, "tst1-1", "reverse", qty=1)
    await _item(app_client, h, "tst1-3", "holo", qty=1)
    await _item(app_client, h, "tst2-1", "normal", qty=3)
    d = (await app_client.get("/api/collection", params={"dupes": True, "sort": "set"}, headers=h)).json()
    assert [(i["card_id"], i["card_total"]) for i in d] == [("tst1-1", 2), ("tst1-1", 2), ("tst2-1", 3)]
