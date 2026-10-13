import pytest

import history
import tcgdex


async def test_collection_history_snapshot_in_gbp(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=h)
    pts = (await app_client.get("/api/collection/history", headers=h)).json()
    assert len(pts) == 1 and pts[0]["value_gbp"] == 85.0 and pts[0]["total_cards"] == 1
    await app_client.post("/api/collection/add", json={"card_id": "tst1-3", "variant": "holo"}, headers=h)
    pts = (await app_client.get("/api/collection/history", headers=h)).json()
    assert len(pts) == 1 and pts[0]["value_gbp"] == 170.0


async def test_card_history_points_and_cardmarket_trend(app_client, make_user):
    u = await make_user()
    h = u["headers"]
    await app_client.get("/api/cards/tst1-1", headers=h)
    d = (await app_client.get("/api/cards/tst1-1/history", headers=h)).json()
    assert d["variants"] == ["normal", "reverse"]
    assert d["points"][-1]["normal_gbp"] == pytest.approx(0.68, abs=0.01)
    assert d["points"][-1]["reverse_usd"] == 2.0
    assert len(d["cardmarket_trend"]) == 4
    assert d["cardmarket_trend"][0]["normal"] == pytest.approx(0.85, abs=0.01)
    assert d["cardmarket_trend"][-1]["holo"] == pytest.approx(1.275, abs=0.01)
    assert (await app_client.get("/api/cards/bad-1/history", headers=h)).status_code == 404


async def test_daily_job_updates_prices_and_snapshots(app_client, make_user, db):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2"}, headers=u["headers"])
    await db.collection_items.update_many({"user_id": u["user"]["id"]}, {"$set": {"price_gbp": None, "price_usd": None}})
    await history.daily_job()
    it = await db.collection_items.find_one({"user_id": u["user"]["id"]})
    assert it["price_usd"] == 3.0 and it["price_gbp"] is not None
    assert await db.value_history.find_one({"user_id": u["user"]["id"]})
    assert (await db.app_meta.find_one({"_id": "daily_job"}))["date"]


async def test_migrate_gbp_fills_missing_values(app_client, make_user, db):
    u = await make_user()
    await app_client.post("/api/collection/add", json={"card_id": "tst1-2"}, headers=u["headers"])
    await db.collection_items.update_many({"user_id": u["user"]["id"]}, {"$unset": {"price_gbp": ""}})
    await history.migrate_gbp()
    it = await db.collection_items.find_one({"user_id": u["user"]["id"]})
    assert it["price_gbp"] == tcgdex.to_gbp(it["price_usd"], it["price_eur"])
