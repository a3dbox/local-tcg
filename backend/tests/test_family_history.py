"""Backend tests for family trading + price/collection history (iteration 2)."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://tcg-binder.preview.emergentagent.com"
API = f"{BASE_URL}/api"
TIMEOUT = 60


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def user_a(s):
    email = f"test_fam_a_{uuid.uuid4().hex[:8]}@test.local"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "name": "FamA"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["access_token"], "id": d["user"]["id"]}


@pytest.fixture(scope="module")
def user_b(s):
    email = f"test_fam_b_{uuid.uuid4().hex[:8]}@test.local"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "name": "FamB"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["access_token"], "id": d["user"]["id"]}


@pytest.fixture(scope="module")
def setup_data(s, user_a, user_b):
    # A adds 3 copies of swsh3-136 normal
    r = s.post(f"{API}/collection/set-qty", json={"card_id": "swsh3-136", "variant": "normal", "quantity": 3},
               headers=auth(user_a["token"]), timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    # B tracks swsh3 goal
    r = s.post(f"{API}/goals", json={"set_id": "swsh3", "target": "base"},
               headers=auth(user_b["token"]), timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return True


class TestFamilyMembers:
    def test_members_excludes_self(self, s, user_a, user_b, setup_data):
        r = s.get(f"{API}/family/members", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        ids = [m["id"] for m in data]
        assert user_a["id"] not in ids
        assert user_b["id"] in ids
        b_member = next(m for m in data if m["id"] == user_b["id"])
        assert "name" in b_member and "items" in b_member

    def test_members_requires_auth(self, s):
        r = s.get(f"{API}/family/members", timeout=TIMEOUT)
        assert r.status_code == 401


class TestFamilyCompare:
    def test_compare_structure(self, s, user_a, user_b, setup_data):
        r = s.get(f"{API}/family/compare/{user_b['id']}", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["other"]["id"] == user_b["id"]
        assert set(d["counts"].keys()) == {"shared", "only_me", "only_them"}
        assert isinstance(d["i_can_give"], list) and isinstance(d["they_can_give"], list)
        # A has swsh3-136 qty 3, B has 0 -> should appear in i_can_give with needed_for_goal True (B tracks swsh3)
        furret = next((c for c in d["i_can_give"] if c["card_id"] == "swsh3-136"), None)
        assert furret is not None, f"Expected swsh3-136 in i_can_give, got {[c['card_id'] for c in d['i_can_give']]}"
        assert furret["needed_for_goal"] is True
        assert furret["spare_variant"] == "normal"
        assert furret["spare_qty"] >= 1

    def test_compare_self_404(self, s, user_a):
        r = s.get(f"{API}/family/compare/{user_a['id']}", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 404

    def test_compare_invalid_id(self, s, user_a):
        r = s.get(f"{API}/family/compare/not-an-objectid", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 404


class TestFamilyGive:
    def test_give_to_self_rejected(self, s, user_a):
        r = s.post(f"{API}/family/give", json={"to_user_id": user_a["id"], "card_id": "swsh3-136",
                                               "variant": "normal", "quantity": 1},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 400

    def test_give_not_enough(self, s, user_a, user_b, setup_data):
        r = s.post(f"{API}/family/give", json={"to_user_id": user_b["id"], "card_id": "swsh3-136",
                                               "variant": "normal", "quantity": 999},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 400

    def test_give_moves_copy_and_logs(self, s, user_a, user_b, setup_data):
        # Give 1 copy of swsh3-136 from A -> B
        r = s.post(f"{API}/family/give", json={"to_user_id": user_b["id"], "card_id": "swsh3-136",
                                               "variant": "normal", "quantity": 1},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        # A should now have qty 2
        r = s.get(f"{API}/collection", headers=auth(user_a["token"]), timeout=TIMEOUT)
        a_items = [it for it in r.json() if it["card_id"] == "swsh3-136" and it["variant"] == "normal"]
        assert a_items and a_items[0]["quantity"] == 2, a_items
        # B should have qty 1
        r = s.get(f"{API}/collection", headers=auth(user_b["token"]), timeout=TIMEOUT)
        b_items = [it for it in r.json() if it["card_id"] == "swsh3-136" and it["variant"] == "normal"]
        assert b_items and b_items[0]["quantity"] == 1, b_items
        # Activity log for A
        r = s.get(f"{API}/family/activity", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        log = r.json()
        assert any(l["card_id"] == "swsh3-136" and l["to_id"] == user_b["id"] for l in log)


class TestHistory:
    def test_collection_history(self, s, user_a):
        r = s.get(f"{API}/collection/history", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list) and len(d) >= 1
        pt = d[-1]
        assert "date" in pt and "value_usd" in pt

    def test_card_history(self, s, user_a):
        # Hit card detail to seed a price history point
        r = s.get(f"{API}/cards/swsh3-136", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        r = s.get(f"{API}/cards/swsh3-136/history", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "points" in d and "variants" in d and "cardmarket_trend" in d
        assert isinstance(d["points"], list) and len(d["points"]) >= 1
        assert isinstance(d["cardmarket_trend"], list)

    def test_card_history_404(self, s, user_a):
        r = s.get(f"{API}/cards/nope-xxx/history", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 404
