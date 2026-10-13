import fakes


async def test_meta_lists_types_rarities_and_sets_with_icons(app_client, make_user):
    u = await make_user()
    d = (await app_client.get("/api/meta", headers=u["headers"])).json()
    assert d["types"] == ["Grass", "Lightning"]
    assert "None" not in d["rarities"]
    assert d["sets"][0]["id"] == "tst2" and d["sets"][0]["icon"].endswith("/tst2/symbol.png")
    assert d["sets"][0]["logo"]


async def test_search_maps_filters_to_tcgdex(app_client, make_user):
    u = await make_user()
    fakes.CALLS.clear()
    r = await app_client.get("/api/cards", params={"q": "Pikachu", "exact": True, "set_id": "tst1", "rarity": "Uncommon",
                                                   "type": "Lightning", "sort": "-name", "page": 2, "size": 10}, headers=u["headers"])
    assert r.status_code == 200
    params = [p for url, p in fakes.CALLS if url.endswith("/cards")][-1]
    assert params["name"] == "eq:Pikachu" and params["set.id"] == "eq:tst1" and params["rarity"] == "eq:Uncommon"
    assert params["types"] == "Lightning" and params["sort:field"] == "name" and params["sort:order"] == "DESC"
    assert params["pagination:page"] == 2 and params["pagination:itemsPerPage"] == 10


async def test_search_results_and_owned_annotation(app_client, make_user):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2", "variant": "normal", "quantity": 2}, headers=u["headers"])
    d = (await app_client.get("/api/cards", params={"q": "pikachu", "size": 50}, headers=u["headers"])).json()
    ids = {c["id"]: c["owned"] for c in d["items"]}
    assert set(ids) == {"tst1-2", "tst1-3", "tst2-1"}
    assert ids["tst1-2"] == 2 and ids["tst1-3"] == 0
    assert d["has_more"] is False


async def test_search_by_pokedex_number(app_client, make_user):
    u = await make_user()
    d = (await app_client.get("/api/cards", params={"dex": 1}, headers=u["headers"])).json()
    assert [c["id"] for c in d["items"]] == ["tst1-1"]


async def test_card_detail_variants_prices_and_history(app_client, make_user, db):
    u = await make_user()
    d = (await app_client.get("/api/cards/tst1-1", headers=u["headers"])).json()
    assert d["card"]["name"] == "Bulbasaur" and d["wishlisted"] is False
    assert [v["type"] for v in d["variants"]] == ["normal", "reverse"]
    assert d["variants"][0]["price_gbp"] is not None and d["variants"][0]["owned"] == 0
    assert d["fx"]["eur_gbp"] == 0.85
    assert await db.card_price_history.find_one({"card_id": "tst1-1"})


async def test_card_detail_404(app_client, make_user):
    u = await make_user()
    assert (await app_client.get("/api/cards/nope-1", headers=u["headers"])).status_code == 404


async def test_sets_list_groups_counts_goals(app_client, make_user):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1"}, headers=u["headers"])
    await app_client.post("/api/goals", json={"set_id": "tst1", "target": "full"}, headers=u["headers"])
    d = (await app_client.get("/api/sets", headers=u["headers"])).json()
    assert d["series"][0]["name"] == "Test Series"
    assert [s["id"] for s in d["series"][0]["sets"]] == ["tst2", "tst1"]
    assert d["owned_counts"] == {"tst1": 1} and d["goals"] == ["tst1"]


async def test_set_detail_progress_and_details(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1", "variant": "reverse"}, headers=h)
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=h)
    d = (await app_client.get("/api/sets/tst1", headers=h)).json()
    assert d["progress"]["base"] == [1, 2] and d["progress"]["full"] == [2, 3]
    assert d["owned"] == {"tst1-1": {"reverse": 1}, "tst1-3": {"holo": 1}} and d["goal"] is None
    det = (await app_client.get("/api/sets/tst1/details", headers=h)).json()
    assert set(det) == {"tst1-1", "tst1-2", "tst1-3"}
    assert det["tst1-3"]["variants"] == ["holo"] and det["tst1-3"]["price_gbp"] == 85.0
    assert (await app_client.get("/api/sets/zzz", headers=h)).status_code == 404
    assert (await app_client.get("/api/sets/zzz/details", headers=h)).status_code == 404


async def test_pokedex_list(app_client, make_user):
    u = await make_user()
    d = (await app_client.get("/api/pokedex", headers=u["headers"])).json()
    assert d == [{"id": 1, "name": "bulbasaur"}, {"id": 25, "name": "pikachu"}]
