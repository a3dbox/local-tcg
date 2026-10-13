"""Iteration 3 integration tests against public URL.
Covers GBP fields, admin accounts, custom sets, storage locations, scan.
"""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@pokebinder.local", "password": "admin123"}


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(**ADMIN)


@pytest.fixture(scope="module")
def user_token():
    email = f"TEST_iter3_{int(time.time())}@pb.local"
    r = requests.post(f"{BASE}/api/auth/register",
                      json={"name": "iter3 user", "email": email, "password": "secret123"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    return r.json()["access_token"], email


# ---------- GBP ----------
class TestGBP:
    def test_card_detail_has_gbp(self, user_token):
        token, _ = user_token
        r = requests.get(f"{BASE}/api/cards/swsh3-136", headers=_hdr(token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "fx" in d, "card detail should expose fx rates"
        fx = d["fx"]
        assert "eur_gbp" in fx and "usd_gbp" in fx, fx
        # variants should include price_gbp
        variants = d.get("variants", [])
        assert variants, "swsh3-136 should have variants"
        assert any("price_gbp" in v for v in variants), f"no price_gbp in variants: {variants}"

    def test_collection_stats_has_value_gbp(self, user_token):
        token, _ = user_token
        r = requests.get(f"{BASE}/api/collection/stats", headers=_hdr(token), timeout=20)
        assert r.status_code == 200
        assert "value_gbp" in r.json(), r.json()

    def test_collection_history_has_value_gbp(self, user_token):
        token, _ = user_token
        r = requests.get(f"{BASE}/api/collection/history", headers=_hdr(token), timeout=20)
        assert r.status_code == 200
        body = r.json()
        pts = body.get("points") if isinstance(body, dict) else body
        assert isinstance(pts, list) and pts, body
        assert "value_gbp" in pts[0], pts[0]


# ---------- Admin ----------
class TestAdmin:
    def test_non_admin_forbidden(self, user_token):
        token, _ = user_token
        r = requests.get(f"{BASE}/api/admin/users", headers=_hdr(token), timeout=20)
        assert r.status_code == 403

    def test_admin_list_users(self, admin_token):
        r = requests.get(f"{BASE}/api/admin/users", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) >= 1
        me = next(u for u in users if u.get("is_self"))
        assert me["role"] == "admin"
        # per-user stats
        assert "cards" in users[0] or "value_gbp" in users[0] or "value" in users[0]

    def test_admin_crud_user(self, admin_token):
        email = f"TEST_adm_{int(time.time())}@pb.local"
        payload = {"name": "created by admin", "email": email, "password": "secret123", "role": "user"}
        r = requests.post(f"{BASE}/api/admin/users", json=payload, headers=_hdr(admin_token), timeout=20)
        assert r.status_code in (200, 201), r.text
        uid = r.json()["id"]

        # new user can log in
        tok = _login(email, "secret123")
        assert tok

        # edit (reset password + rename)
        r = requests.patch(f"{BASE}/api/admin/users/{uid}",
                           json={"name": "renamed", "password": "newpass123"},
                           headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "renamed"
        tok2 = _login(email, "newpass123")
        assert tok2

        # delete
        r = requests.delete(f"{BASE}/api/admin/users/{uid}", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200
        # can't log in after delete
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "newpass123"}, timeout=20)
        assert r.status_code in (400, 401, 404)

    def test_admin_cannot_delete_self(self, admin_token):
        users = requests.get(f"{BASE}/api/admin/users", headers=_hdr(admin_token), timeout=20).json()
        me = next(u for u in users if u.get("is_self"))
        r = requests.delete(f"{BASE}/api/admin/users/{me['id']}", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 400

    def test_admin_cannot_change_own_role(self, admin_token):
        users = requests.get(f"{BASE}/api/admin/users", headers=_hdr(admin_token), timeout=20).json()
        me = next(u for u in users if u.get("is_self"))
        r = requests.patch(f"{BASE}/api/admin/users/{me['id']}",
                           json={"role": "user"}, headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 400


# ---------- Custom sets ----------
class TestCustomSets:
    def test_create_rule_based(self, user_token):
        token, _ = user_token
        payload = {"name": "TEST all Squirtle", "description": "", "rules": {"dex": 7}, "card_ids": []}
        r = requests.post(f"{BASE}/api/custom-sets", json=payload, headers=_hdr(token), timeout=60)
        assert r.status_code == 200, r.text
        cs = r.json()
        assert cs["name"] == "TEST all Squirtle"
        assert cs["progress"][1] >= 1, f"rule-based set should resolve >=1 card: {cs}"
        cs_id = cs["id"]

        # detail
        r = requests.get(f"{BASE}/api/custom-sets/{cs_id}", headers=_hdr(token), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "cards" in d and len(d["cards"]) >= 1

        # delete
        r = requests.delete(f"{BASE}/api/custom-sets/{cs_id}", headers=_hdr(token), timeout=20)
        assert r.status_code == 200

    def test_create_hand_picked(self, user_token):
        token, _ = user_token
        payload = {"name": "TEST hand picked", "description": "", "rules": {}, "card_ids": ["swsh3-136"]}
        r = requests.post(f"{BASE}/api/custom-sets", json=payload, headers=_hdr(token), timeout=30)
        assert r.status_code == 200, r.text
        cs = r.json()
        cs_id = cs["id"]
        assert cs["progress"][1] == 1

        # add another card
        r = requests.post(f"{BASE}/api/custom-sets/{cs_id}/cards",
                          json={"card_id": "swsh3-7"}, headers=_hdr(token), timeout=30)
        assert r.status_code == 200
        r = requests.get(f"{BASE}/api/custom-sets/{cs_id}", headers=_hdr(token), timeout=30)
        assert r.json()["progress"][1] == 2

        # remove
        r = requests.delete(f"{BASE}/api/custom-sets/{cs_id}/cards/swsh3-7",
                            headers=_hdr(token), timeout=20)
        assert r.status_code == 200
        r = requests.get(f"{BASE}/api/custom-sets/{cs_id}", headers=_hdr(token), timeout=30)
        assert r.json()["progress"][1] == 1

        requests.delete(f"{BASE}/api/custom-sets/{cs_id}", headers=_hdr(token), timeout=20)


# ---------- Storage ----------
class TestStorage:
    def test_locations_crud_and_move(self, user_token):
        token, _ = user_token

        # create location
        r = requests.post(f"{BASE}/api/locations",
                          json={"name": "TEST Binder", "kind": "binder"},
                          headers=_hdr(token), timeout=20)
        assert r.status_code in (200, 201), r.text
        loc = r.json()
        loc_id = loc["id"]

        # list has unassigned + new location
        r = requests.get(f"{BASE}/api/locations", headers=_hdr(token), timeout=20)
        assert r.status_code == 200
        body = r.json()
        locs = body.get("locations") if isinstance(body, dict) else body
        assert isinstance(locs, list)
        ids = [l["id"] for l in locs]
        assert loc_id in ids
        assert isinstance(body.get("unassigned"), dict) and "value_gbp" in body["unassigned"]

        # add card to collection using correct endpoint
        r = requests.post(f"{BASE}/api/collection/add",
                          json={"card_id": "swsh3-136", "variant": "normal", "quantity": 1},
                          headers=_hdr(token), timeout=20)
        assert r.status_code == 200, r.text

        # find item id via /api/collection
        r = requests.get(f"{BASE}/api/collection", headers=_hdr(token), timeout=20)
        items = r.json()
        item = next((x for x in items if x["card_id"] == "swsh3-136"), None)
        assert item, items
        item_id = item["id"]

        # move 1 copy from unassigned -> new location
        r = requests.post(f"{BASE}/api/locations/move",
                          json={"item_id": item_id, "from_id": "unassigned",
                                "to_id": loc_id, "quantity": 1},
                          headers=_hdr(token), timeout=20)
        assert r.status_code == 200, r.text

        # location detail should list the item
        r = requests.get(f"{BASE}/api/locations/{loc_id}", headers=_hdr(token), timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["cards"] >= 1 and d["items"], d

        # list again - new location shows cards count
        r = requests.get(f"{BASE}/api/locations", headers=_hdr(token), timeout=20)
        loc_entry = next(l for l in r.json()["locations"] if l["id"] == loc_id)
        assert loc_entry["cards"] >= 1

        # delete location
        r = requests.delete(f"{BASE}/api/locations/{loc_id}", headers=_hdr(token), timeout=20)
        assert r.status_code in (200, 204)


# ---------- Scanner ----------
class TestScanner:
    def test_scan_furret_sample(self, user_token):
        token, _ = user_token
        path = "/app/tests/scan_sample_furret.jpg"
        if not os.path.exists(path):
            pytest.skip("sample image missing")
        with open(path, "rb") as f:
            r = requests.post(f"{BASE}/api/scan",
                              files={"file": ("furret.jpg", f, "image/jpeg")},
                              headers=_hdr(token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # expect at least one match with swsh3-136 near the top
        matches = d.get("matches") or [d] if isinstance(d, dict) else d
        top_ids = [m.get("card_id") or m.get("id") for m in (matches if isinstance(matches, list) else [matches])]
        assert "swsh3-136" in top_ids, f"expected swsh3-136 in top matches, got {top_ids}"
