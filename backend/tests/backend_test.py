"""End-to-end backend tests for PokeBinder.

Covers: auth (register/login/me/refresh/isolation), cards search, card detail,
sets listing/detail, goals, collection add/qty/list/stats/export, wishlist,
pokedex, dashboard, scanner (index + recognize).
"""
import os
import io
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://tcg-binder.preview.emergentagent.com"
API = f"{BASE_URL}/api"
SAMPLE_IMG = "/app/tests/scan_sample_furret.jpg"
TIMEOUT = 60


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json={"email": "admin@pokebinder.local", "password": "admin123"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def user_a(s):
    email = f"test_a_{uuid.uuid4().hex[:8]}@test.local"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "name": "User A"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["access_token"], "refresh": d["refresh_token"], "id": d["user"]["id"]}


@pytest.fixture(scope="session")
def user_b(s):
    email = f"test_b_{uuid.uuid4().hex[:8]}@test.local"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "name": "User B"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["access_token"], "refresh": d["refresh_token"], "id": d["user"]["id"]}


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- auth ----------
class TestAuth:
    def test_register_login_me(self, s, user_a):
        r = s.post(f"{API}/auth/login", json={"email": user_a["email"], "password": "secret123"}, timeout=TIMEOUT)
        assert r.status_code == 200
        tok = r.json()["access_token"]
        assert isinstance(tok, str) and len(tok) > 20
        r = s.get(f"{API}/auth/me", headers=auth(tok), timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["email"] == user_a["email"]

    def test_wrong_password(self, s, user_a):
        r = s.post(f"{API}/auth/login", json={"email": user_a["email"], "password": "WRONG"}, timeout=TIMEOUT)
        assert r.status_code == 401

    def test_me_requires_auth(self, s):
        r = s.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_refresh(self, s, user_a):
        r = s.post(f"{API}/auth/refresh", json={"refresh_token": user_a["refresh"]}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert "access_token" in r.json()


# ---------- cards / meta ----------
class TestCards:
    def test_meta(self, s, admin_headers):
        r = s.get(f"{API}/meta", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["types"], list) and len(d["types"]) > 0
        assert isinstance(d["sets"], list) and len(d["sets"]) > 0

    def test_search_charizard(self, s, admin_headers):
        r = s.get(f"{API}/cards", params={"q": "charizard", "size": 12}, headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        assert all("id" in c and "name" in c for c in items)
        assert any("charizard" in c["name"].lower() for c in items)

    def test_card_detail_furret(self, s, admin_headers):
        r = s.get(f"{API}/cards/swsh3-136", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["card"]["id"] == "swsh3-136"
        assert isinstance(d["variants"], list) and len(d["variants"]) > 0

    def test_card_detail_404(self, s, admin_headers):
        r = s.get(f"{API}/cards/nope-xxx", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 404


# ---------- sets ----------
class TestSets:
    def test_list_sets(self, s, admin_headers):
        r = s.get(f"{API}/sets", headers=admin_headers, timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["series"], list) and len(d["series"]) > 0
        assert "sets" in d["series"][0]

    def test_set_detail_swsh3(self, s, admin_headers):
        r = s.get(f"{API}/sets/swsh3", headers=admin_headers, timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert d["set"]["id"] == "swsh3"
        assert "progress" in d


# ---------- collection & goals, with user isolation ----------
class TestCollectionIsolation:
    def test_add_to_user_a_not_visible_to_b(self, s, user_a, user_b):
        r = s.post(f"{API}/collection/add", json={"card_id": "swsh3-136", "variant": "normal", "quantity": 2},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        # A sees it
        r = s.get(f"{API}/collection", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        items_a = r.json()
        assert any(it["card_id"] == "swsh3-136" for it in items_a)
        # B does not
        r = s.get(f"{API}/collection", headers=auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        assert not any(it["card_id"] == "swsh3-136" for it in r.json())

    def test_set_qty_persist_and_detail_owned(self, s, user_a):
        r = s.post(f"{API}/collection/set-qty", json={"card_id": "swsh3-136", "variant": "normal", "quantity": 5},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200 and r.json()["quantity"] == 5
        r = s.get(f"{API}/cards/swsh3-136", headers=auth(user_a["token"]), timeout=TIMEOUT)
        v = next(v for v in r.json()["variants"] if v["type"] == "normal")
        assert v["owned"] == 5

    def test_stats(self, s, user_a):
        r = s.get(f"{API}/collection/stats", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["total_cards"] >= 5 and d["unique_cards"] >= 1

    def test_export_csv(self, s, user_a):
        r = s.get(f"{API}/collection/export", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        txt = r.text
        assert "card_id" in txt and "swsh3-136" in txt


class TestGoals:
    def test_create_list_delete(self, s, user_a):
        r = s.post(f"{API}/goals", json={"set_id": "swsh3", "target": "base"},
                   headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        r = s.get(f"{API}/goals", headers=auth(user_a["token"]), timeout=120)
        assert r.status_code == 200
        goals = r.json()
        assert any(g["set_id"] == "swsh3" for g in goals)
        r = s.delete(f"{API}/goals/swsh3", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200


class TestWishlist:
    def test_toggle(self, s, user_a):
        r = s.post(f"{API}/wishlist/swsh3-136", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["wishlisted"] is True
        r = s.get(f"{API}/wishlist", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert any(d["card_id"] == "swsh3-136" for d in r.json())
        r = s.post(f"{API}/wishlist/swsh3-136", headers=auth(user_a["token"]), timeout=TIMEOUT)
        assert r.json()["wishlisted"] is False


# ---------- pokedex & dashboard ----------
class TestMisc:
    def test_pokedex(self, s, admin_headers):
        r = s.get(f"{API}/pokedex", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert any(x["id"] == 25 and x["name"] == "pikachu" for x in d)

    def test_dashboard(self, s, user_a):
        r = s.get(f"{API}/dashboard", headers=auth(user_a["token"]), timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert "stats" in d and "recent" in d and "goals" in d


# ---------- scanner ----------
class TestScanner:
    def test_index_build_single_set(self, s, admin_headers):
        r = s.post(f"{API}/scan/index", json={"set_ids": ["swsh3"]}, headers=admin_headers, timeout=TIMEOUT)
        # 200 if not running, 409 if a previous task is running
        assert r.status_code in (200, 409), r.text
        # poll status briefly
        for _ in range(30):
            st = s.get(f"{API}/scan/index/status", headers=admin_headers, timeout=TIMEOUT).json()
            if not st.get("running"):
                break
            time.sleep(2)
        st = s.get(f"{API}/scan/index/status", headers=admin_headers, timeout=TIMEOUT).json()
        assert "running" in st

    def test_scan_recognizes_furret(self, s, admin_headers):
        with open(SAMPLE_IMG, "rb") as f:
            files = {"file": ("furret.jpg", f, "image/jpeg")}
            r = s.post(f"{API}/scan", files=files, headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("matches"), list) and len(d["matches"]) > 0
        top = d["matches"][0]
        assert top["card_id"] == "swsh3-136", f"expected swsh3-136 got {top}"
        assert d.get("confidence") == "high", f"expected high confidence, got {d.get('confidence')}"
