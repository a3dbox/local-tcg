import os
import sys
import uuid
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ["DB_NAME"] = f"pokebinder_unittest_{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
os.environ.pop("OLLAMA_URL", None)

import httpx  # noqa: E402
import pytest  # noqa: E402

import tcgdex  # noqa: E402
import history  # noqa: E402
import scanner  # noqa: E402
import fakes  # noqa: E402

tcgdex.fetch_url = fakes.make_fake_fetch(tcgdex)
tcgdex.http = fakes.FakeHttp()


async def _noop(*a, **kw):
    return None


history.daily_loop = _noop

import server  # noqa: E402
from database import client as mongo_client  # noqa: E402


@pytest.fixture(scope="session")
async def app_client():
    await mongo_client.drop_database(os.environ["DB_NAME"])
    await server.startup()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as c:
        yield c
    await mongo_client.drop_database(os.environ["DB_NAME"])


@pytest.fixture
def db():
    from database import db as _db
    return _db


@pytest.fixture
async def make_user(app_client):
    async def _make(name="Trainer", password="secret12"):
        email = f"{name.lower()}-{uuid.uuid4().hex[:8]}@test.io"
        r = await app_client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
        assert r.status_code == 200, r.text
        d = r.json()
        return {"headers": {"Authorization": f"Bearer {d['access_token']}"}, "user": d["user"], "email": email,
                "password": password, "refresh": d["refresh_token"]}
    return _make


@pytest.fixture
async def admin(app_client):
    r = await app_client.post("/api/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"headers": {"Authorization": f"Bearer {d['access_token']}"}, "user": d["user"]}


@pytest.fixture
def reset_scanner():
    scanner._idx.update({"ids": [], "P": [], "A": [], "C": [], "meta": {}, "mat": None, "loaded": False})
    yield
