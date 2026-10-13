async def test_goal_crud_and_progress(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    assert (await app_client.post("/api/goals", json={"set_id": "tst1", "target": "everything"}, headers=h)).status_code == 400
    await app_client.post("/api/goals", json={"set_id": "tst1", "target": "base"}, headers=h)
    await app_client.post("/api/collection/add", json={"card_id": "tst1-1"}, headers=h)
    g = (await app_client.get("/api/goals", headers=h)).json()
    assert len(g) == 1 and g[0]["target"] == "base" and g[0]["name"] == "Test Set"
    assert g[0]["progress"]["base"] == [1, 2]
    await app_client.post("/api/goals", json={"set_id": "tst1", "target": "master"}, headers=h)
    g = (await app_client.get("/api/goals", headers=h)).json()
    assert len(g) == 1 and g[0]["target"] == "master" and g[0]["progress"]["master"] == [1, 5]
    assert (await app_client.get("/api/sets/tst1", headers=h)).json()["goal"] == "master"
    await app_client.delete("/api/goals/tst1", headers=h)
    assert (await app_client.get("/api/goals", headers=h)).json() == []


async def test_goals_are_private(app_client, make_user):
    a, b = await make_user("A"), await make_user("B")
    await app_client.post("/api/goals", json={"set_id": "tst2"}, headers=a["headers"])
    assert (await app_client.get("/api/goals", headers=b["headers"])).json() == []
