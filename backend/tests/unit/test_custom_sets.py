async def _create(c, h, **body):
    r = await c.post("/api/custom-sets", json={"name": "My set", **body}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_rule_based_set_all_lightning(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    cs = await _create(app_client, h, name="All Lightning", rules={"type": "Lightning"})
    assert cs["progress"] == [0, 3]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2"}, headers=h)
    d = (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).json()
    assert {c["id"] for c in d["cards"]} == {"tst1-2", "tst1-3", "tst2-1"}
    assert d["progress"] == [1, 3] and "tst1-2" in d["owned"]
    assert next(c for c in d["cards"] if c["id"] == "tst2-1")["set_name"] == "Second Set"


async def test_pokemon_by_dex_and_by_name(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    by_dex = await _create(app_client, h, name="Every Pikachu", rules={"dex": 25})
    assert by_dex["progress"][1] == 3
    exact = await _create(app_client, h, name="Plain Pikachu", rules={"q": "Pikachu", "exact": True})
    assert exact["progress"][1] == 2


async def test_manual_selection_add_and_remove(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    cs = await _create(app_client, h, name="Favourites", card_ids=["tst1-1", "tst1-1"])
    assert cs["progress"] == [0, 1] and cs["card_ids"] == ["tst1-1"]
    assert (await app_client.post(f"/api/custom-sets/{cs['id']}/cards", json={"card_id": "tst2-1"}, headers=h)).status_code == 200
    assert (await app_client.post(f"/api/custom-sets/{cs['id']}/cards", json={"card_id": "bad-1"}, headers=h)).status_code == 404
    d = (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).json()
    assert {c["id"] for c in d["cards"]} == {"tst1-1", "tst2-1"}
    await app_client.delete(f"/api/custom-sets/{cs['id']}/cards/tst1-1", headers=h)
    d = (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).json()
    assert [c["id"] for c in d["cards"]] == ["tst2-1"]


async def test_rules_plus_exclusions_and_extras(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    cs = await _create(app_client, h, rules={"type": "Lightning"}, card_ids=["tst1-1"])
    assert cs["progress"][1] == 4
    await app_client.delete(f"/api/custom-sets/{cs['id']}/cards/tst1-3", headers=h)
    d = (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).json()
    assert {c["id"] for c in d["cards"]} == {"tst1-1", "tst1-2", "tst2-1"} and d["excluded_ids"] == ["tst1-3"]
    await app_client.post(f"/api/custom-sets/{cs['id']}/cards", json={"card_id": "tst1-3"}, headers=h)
    d = (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).json()
    assert len(d["cards"]) == 4 and d["excluded_ids"] == []


async def test_update_list_delete_and_privacy(app_client, make_user):
    u, other = await make_user(), await make_user("Other")
    h = u["headers"]
    cs = await _create(app_client, h, rules={"type": "Grass"})
    d = (await app_client.patch(f"/api/custom-sets/{cs['id']}", json={"name": "Renamed", "rules": {"rarity": "Ultra Rare"}}, headers=h)).json()
    assert d["name"] == "Renamed" and [c["id"] for c in d["cards"]] == ["tst1-3"]
    assert (await app_client.patch(f"/api/custom-sets/{cs['id']}", json={"name": " "}, headers=h)).status_code == 400
    lst = (await app_client.get("/api/custom-sets", headers=h)).json()
    assert [x["name"] for x in lst] == ["Renamed"] and lst[0]["cover"]
    assert (await app_client.get("/api/custom-sets", headers=other["headers"])).json() == []
    assert (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=other["headers"])).status_code == 404
    assert (await app_client.delete(f"/api/custom-sets/{cs['id']}", headers=h)).status_code == 200
    assert (await app_client.get(f"/api/custom-sets/{cs['id']}", headers=h)).status_code == 404


async def test_create_validation(app_client, make_user):
    u = await make_user()
    assert (await app_client.post("/api/custom-sets", json={"name": " "}, headers=u["headers"])).status_code == 400
    empty = await _create(app_client, u["headers"], name="Empty")
    assert empty["progress"] == [0, 0]
