import asyncio

import cv2
import numpy as np
from PIL import Image

import scanner
import fakes


def test_detect_card_straightens_photo():
    img = cv2.imdecode(np.frombuffer(fakes.photo_of("tst1-2"), np.uint8), cv2.IMREAD_COLOR)
    card, detected = scanner.detect_card(img)
    assert detected is True and card.shape[:2] == (scanner.H, scanner.W)


def test_detect_card_fallback_rotates_landscape():
    card, detected = scanner.detect_card(np.zeros((300, 600, 3), np.uint8))
    assert detected is False and card.shape[:2] == (scanner.H, scanner.W)


def _vec(bgr):
    return scanner._vec(*scanner.feats(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))


def test_fingerprint_distance_same_card_smaller_than_other():
    photo = cv2.imdecode(np.frombuffer(fakes.photo_of("tst1-2"), np.uint8), cv2.IMREAD_COLOR)
    warped, _ = scanner.detect_card(photo)
    q = _vec(warped)
    same, other = _vec(fakes.card_art(22)), _vec(fakes.card_art(33))
    d_same = scanner._dist(*q, same[0][None], same[1][None], same[2][None])[0]
    d_other = scanner._dist(*q, other[0][None], other[1][None], other[2][None])[0]
    assert d_same < d_other and d_same < 0.3


def test_ocr_info_shape():
    out = scanner.ocr_info(fakes.card_art(1, scanner.W, scanner.H))
    assert set(out) == {"numbers", "words", "raw"} and isinstance(out["numbers"], list)


def test_number_regex():
    assert scanner.NUM_RE.findall("Illus. x  136/189 ◆") == [("136", "189")]
    assert scanner.NUM_RE.findall("TG12/TG30") == [("TG12", "TG30")]


def test_same_num():
    assert scanner._same_num("007", "7") and scanner._same_num("TG12", "tg12") and not scanner._same_num("8", "9")


async def test_index_build_and_status(app_client, make_user, reset_scanner):
    u = await make_user()
    h = u["headers"]
    r = await app_client.post("/api/scan/index", json={"set_ids": ["tst1"]}, headers=h)
    assert r.status_code == 200
    for _ in range(100):
        st = (await app_client.get("/api/scan/index/status", headers=h)).json()
        if not st["running"] and st["indexed"] >= 3:
            break
        await asyncio.sleep(0.05)
    assert st["indexed"] == 3 and st["done"] == 1 and st["total"] == 1


async def test_index_goals_only_requires_goals(app_client, make_user):
    u = await make_user()
    assert (await app_client.post("/api/scan/index", json={"goals_only": True}, headers=u["headers"])).status_code == 400


async def test_scan_recognises_card_from_photo(app_client, make_user, reset_scanner, db):
    await scanner.build_index(db)
    u = await make_user()
    r = await app_client.post("/api/scan", files=fakes.as_file(fakes.photo_of("tst1-2")), headers=u["headers"])
    assert r.status_code == 200
    d = r.json()
    assert d["detected"] is True
    assert d["matches"][0]["card_id"] == "tst1-2"
    assert d["matches"][0]["set_name"] == "Test Set" and d["matches"][0]["variants"] == ["normal", "reverse"]
    assert "price_gbp" in d["matches"][0]
    assert d["confidence"] in ("high", "medium", "low")


async def test_scan_bad_image(app_client, make_user):
    u = await make_user()
    r = await app_client.post("/api/scan", files={"file": ("x.jpg", b"notanimage", "image/jpeg")}, headers=u["headers"])
    assert r.status_code == 200 and r.json()["matches"] == []
