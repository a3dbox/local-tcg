"""Fake TCGdex / PokeAPI / FX data so unit tests never hit the network."""
import copy
import io

import cv2
import numpy as np

IMG = "https://img.test"

SET_BRIEF = [
    {"id": "tst1", "name": "Test Set", "logo": f"{IMG}/tst1/logo", "cardCount": {"official": 2, "total": 3}},
    {"id": "tst2", "name": "Second Set", "logo": f"{IMG}/tst2/logo", "cardCount": {"official": 1, "total": 1}},
]


def _brief(cid, local, name):
    s = cid.split("-")[0]
    return {"id": cid, "localId": local, "name": name, "image": f"{IMG}/{s}/{local}"}


SETS = {
    "tst1": {"id": "tst1", "name": "Test Set", "logo": f"{IMG}/tst1/logo", "releaseDate": "2024-01-01",
             "serie": {"id": "tst", "name": "Test Series"},
             "cardCount": {"official": 2, "total": 3, "normal": 2, "holo": 1, "reverse": 2, "firstEd": 0},
             "cards": [_brief("tst1-1", "1", "Bulbasaur"), _brief("tst1-2", "2", "Pikachu"), _brief("tst1-3", "3", "Pikachu ex")]},
    "tst2": {"id": "tst2", "name": "Second Set", "logo": f"{IMG}/tst2/logo", "releaseDate": "2024-06-01",
             "serie": {"id": "tst", "name": "Test Series"}, "cardCount": {"official": 1, "total": 1, "normal": 1},
             "cards": [_brief("tst2-1", "1", "Pikachu")]},
}


def _card(cid, name, set_id, **kw):
    s = SETS[set_id]
    local = cid.split("-")[1]
    base = {"id": cid, "localId": local, "name": name, "image": f"{IMG}/{set_id}/{local}", "category": "Pokemon",
            "set": {"id": set_id, "name": s["name"], "cardCount": {"official": s["cardCount"]["official"], "total": s["cardCount"]["total"]}}}
    base.update(kw)
    return base


CARDS = {
    "tst1-1": _card("tst1-1", "Bulbasaur", "tst1", rarity="Common", types=["Grass"], dexId=[1],
                    variants={"normal": True, "reverse": True, "holo": False},
                    pricing={"tcgplayer": {"normal": {"marketPrice": 1.0}, "reverse-holofoil": {"marketPrice": 2.0}},
                             "cardmarket": {"trend": 0.8, "avg": 0.9, "avg30": 1.0, "avg7": 0.9, "avg1": 0.85, "trend-holo": 1.5}}),
    "tst1-2": _card("tst1-2", "Pikachu", "tst1", rarity="Uncommon", types=["Lightning"], dexId=[25],
                    variants_detailed=[{"type": "normal"}, {"type": "reverse"}],
                    pricing={"tcgplayer": {"normal": {"marketPrice": 3.0}, "reverse-holofoil": {"midPrice": 4.0}}}),
    "tst1-3": _card("tst1-3", "Pikachu ex", "tst1", rarity="Ultra Rare", types=["Lightning"], dexId=[25],
                    variants={"holo": True}, pricing={"cardmarket": {"trend": 100.0}}),
    "tst2-1": _card("tst2-1", "Pikachu", "tst2", rarity="Promo", types=["Lightning"], dexId=[25], variants={"normal": True}),
}

SERIES = [{"id": "tst", "name": "Test Series"}]
SERIES_FULL = {"tst": {"id": "tst", "name": "Test Series", "releaseDate": "2024-01-01", "sets": SET_BRIEF},
               "tcgp": {"id": "tcgp", "name": "Pocket", "sets": [{"id": "P-A"}]}}
SPECIES = {"results": [{"name": "bulbasaur", "url": "https://poke.test/pokemon-species/1/"},
                       {"name": "pikachu", "url": "https://poke.test/pokemon-species/25/"}]}
FX = {"rates": {"GBP": 0.85, "USD": 1.10}}
CALLS = []


def _match(v, rule):
    if rule.startswith("eq:"):
        return str(v).lower() == rule[3:].lower()
    return rule.lower() in str(v).lower()


def search(params):
    out = []
    for c in CARDS.values():
        if "name" in params and not _match(c["name"], params["name"]):
            continue
        if "set.id" in params and not _match(c["set"]["id"], params["set.id"]):
            continue
        if "rarity" in params and not _match(c.get("rarity"), params["rarity"]):
            continue
        if "types" in params and not any(_match(t, params["types"]) for t in c.get("types", [])):
            continue
        if "dexId" in params and int(params["dexId"][3:]) not in c.get("dexId", []):
            continue
        if "localId" in params and not _match(c["localId"], params["localId"]):
            continue
        if "category" in params and not _match(c["category"], params["category"]):
            continue
        out.append({k: c[k] for k in ("id", "localId", "name", "image")})
    return out


def make_fake_fetch(tcgdex):
    async def fake_fetch_url(_db, url, params=None, ttl=None):
        params = dict(params or {})
        CALLS.append((url, params))
        if url.startswith(tcgdex.FX_BASE):
            return copy.deepcopy(FX)
        if url.startswith(tcgdex.POKEAPI):
            return copy.deepcopy(SPECIES)
        path = url[len(tcgdex.BASE):]
        if path == "/cards":
            return search(params)
        if path.startswith("/cards/"):
            return copy.deepcopy(CARDS.get(path[7:]))
        if path == "/sets":
            return copy.deepcopy(SET_BRIEF)
        if path.startswith("/sets/"):
            return copy.deepcopy(SETS.get(path[6:]))
        if path == "/series":
            return copy.deepcopy(SERIES)
        if path.startswith("/series/"):
            return copy.deepcopy(SERIES_FULL.get(path[8:]))
        if path == "/types":
            return ["Grass", "Lightning"]
        if path == "/rarities":
            return ["Common", "None", "Uncommon"]
        return None
    return fake_fetch_url


def card_art(seed: int, w=490, h=684) -> np.ndarray:
    """Deterministic, visually distinct synthetic 'card' image (BGR)."""
    rng = np.random.default_rng(seed)
    img = np.full((h, w, 3), rng.integers(80, 255, 3), np.uint8)
    cv2.rectangle(img, (0, 0), (w - 1, h - 1), (20, 200, 240), 18)
    for _ in range(14):
        color = tuple(int(x) for x in rng.integers(0, 255, 3))
        p1 = tuple(int(x) for x in (rng.integers(20, w - 20), rng.integers(40, h // 2 + 80)))
        if rng.random() < .5:
            cv2.circle(img, p1, int(rng.integers(20, 90)), color, -1)
        else:
            p2 = (min(w - 20, p1[0] + int(rng.integers(30, 160))), min(h - 20, p1[1] + int(rng.integers(30, 160))))
            cv2.rectangle(img, p1, p2, color, -1)
    return img


SEEDS = {"tst1-1": 11, "tst1-2": 22, "tst1-3": 33, "tst2-1": 44}


def png_bytes(img) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def photo_of(card_id: str) -> bytes:
    """Card placed on a noisy table at an angle, like a phone photo."""
    c = card_art(SEEDS[card_id])
    h, w = c.shape[:2]
    rng = np.random.default_rng(7)
    bg = np.full((1300, 1000, 3), (55, 85, 65), np.uint8) + rng.integers(0, 25, (1300, 1000, 3), dtype=np.uint8)
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]),
                                    np.float32([[170, 150], [800, 190], [830, 1100], [140, 1080]]))
    warped = cv2.warpPerspective(c, M, (1000, 1300))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), M, (1000, 1300))
    bg[mask > 0] = warped[mask > 0]
    ok, buf = cv2.imencode(".jpg", bg, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()


class FakeResp:
    def __init__(self, content, status=200):
        self.content, self.status_code = content, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class FakeHttp:
    async def get(self, url, **kw):
        for cid, seed in SEEDS.items():
            s, n = cid.split("-")
            if url == f"{IMG}/{s}/{n}/low.png":
                return FakeResp(png_bytes(card_art(seed)))
        return FakeResp(b"", 404)

    async def post(self, *a, **kw):
        raise RuntimeError("no network in tests")


def as_file(data: bytes):
    return {"file": ("scan.jpg", io.BytesIO(data), "image/jpeg")}
