import os
import re
import io
import json
import base64
import asyncio
import difflib
import logging

import cv2
import numpy as np
import imagehash
import pytesseract
from PIL import Image

import tcgdex

log = logging.getLogger("scanner")
W, H = 600, 836
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint16)
NUM_RE = re.compile(r"([A-Z]{0,5}\d{1,3}[a-z]?)\s*[/\\|]\s*([A-Z]{0,5}\d{2,3})")
STOP = {"basic", "stage", "evolves", "from", "trainer", "item", "supporter", "energy", "tool", "pokemon",
        "pokémon", "stadium", "special", "put", "this", "card", "onto", "the", "bench", "ability", "lv"}
status = {"running": False, "done": 0, "total": 0, "current": None, "errors": 0}
_idx = {"ids": [], "P": [], "A": [], "C": [], "meta": {}, "mat": None, "loaded": False}


# ---------- image processing ----------
def _order(pts):
    pts = pts.reshape(4, 2).astype("float32")
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def detect_card(bgr):
    h, w = bgr.shape[:2]
    s = min(1.0, 1000 / max(h, w))
    small = cv2.resize(bgr, None, fx=s, fy=s) if s < 1 else bgr
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(gray, 40, 140), np.ones((3, 3), np.uint8), iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = small.shape[0] * small.shape[1]
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:6]:
        if cv2.contourArea(c) < 0.25 * area:
            break
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        approx = next((a for a in (cv2.approxPolyDP(hull, e * peri, True) for e in (0.02, 0.03, 0.05, 0.08)) if len(a) == 4), None)
        if approx is None:
            approx = cv2.boxPoints(cv2.minAreaRect(hull)).reshape(4, 1, 2)
        pts = _order(approx) / s
        wl, hl = np.linalg.norm(pts[1] - pts[0]), np.linalg.norm(pts[3] - pts[0])
        if wl > hl:
            pts = np.array([pts[1], pts[2], pts[3], pts[0]], dtype="float32")
            wl, hl = hl, wl
        if not 0.6 < wl / max(hl, 1) < 0.82:
            continue
        M = cv2.getPerspectiveTransform(pts, np.float32([[0, 0], [W, 0], [W, H], [0, H]]))
        return cv2.warpPerspective(bgr, M, (W, H)), True
    if w > h:
        bgr = cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    return cv2.resize(bgr, (W, H)), False


def feats(pil: Image.Image):
    pil = pil.convert("RGB").resize((W, H))
    art = pil.crop((int(.08 * W), int(.10 * H), int(.92 * W), int(.53 * H)))
    p, a = imagehash.phash(pil, 16), imagehash.phash(art, 16)
    c = np.asarray(art.resize((6, 4), Image.BILINEAR), dtype=np.uint8).flatten()
    return str(p), str(a), c.tobytes().hex()


def _bits(hexs):
    return np.packbits(imagehash.hex_to_hash(hexs).hash.flatten())


def _vec(p, a, c):
    return _bits(p), _bits(a), np.frombuffer(bytes.fromhex(c), dtype=np.uint8)


def _dist(qp, qa, qc, P, A, C):
    dp = POP[np.bitwise_xor(P, qp)].sum(1) / 256.0
    da = POP[np.bitwise_xor(A, qa)].sum(1) / 256.0
    dc = np.abs(C.astype(np.int16) - qc.astype(np.int16)).mean(1) / 128.0
    return 0.35 * dp + 0.45 * da + 0.20 * np.clip(dc, 0, 1)


def ocr_info(card_bgr):
    gray = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    hh = big.shape[0]
    bottom, top = big[int(.86 * hh):, :], big[:int(.12 * hh), :]
    texts = []
    for img in (bottom, cv2.threshold(bottom, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
        try:
            texts.append(pytesseract.image_to_string(img, config="--psm 11"))
        except Exception as e:  # noqa
            log.warning("ocr failed %s", e)
    numbers = []
    for t in texts:
        for a, b in NUM_RE.findall(t):
            if (a, b) not in numbers:
                numbers.append((a, b))
    words = []
    try:
        name_txt = pytesseract.image_to_string(top, config="--psm 6")
        for w in re.findall(r"[A-Za-zé'\-]{3,}", name_txt):
            if w.lower() not in STOP and w.lower() not in [x.lower() for x in words]:
                words.append(w)
    except Exception as e:  # noqa
        log.warning("ocr failed %s", e)
    return {"numbers": numbers[:3], "words": sorted(words, key=len, reverse=True)[:3], "raw": " | ".join(t.strip() for t in texts)[:300]}


async def ollama_read(data: bytes):
    url, model = os.environ.get("OLLAMA_URL"), os.environ.get("OLLAMA_MODEL")
    if not url or not model:
        return None
    try:
        r = await tcgdex.http.post(url.rstrip("/") + "/api/generate", timeout=90, json={
            "model": model, "stream": False, "format": "json", "images": [base64.b64encode(data).decode()],
            "prompt": "This photo shows a Pokemon trading card. Reply ONLY with JSON: "
                      "{\"name\": \"card name\", \"number\": \"collector number e.g. 136/189\"}"})
        return json.loads(r.json().get("response") or "{}")
    except Exception as e:  # noqa
        log.warning("ollama failed %s", e)
        return None


# ---------- index ----------
async def load_index(db):
    if _idx["loaded"]:
        return
    async for d in db.card_hashes.find({}):
        _add_mem(d)
    _idx["loaded"] = True


def _add_mem(d):
    if d["_id"] in _idx["meta"]:
        return
    p, a, c = _vec(d["p"], d["a"], d["c"])
    _idx["ids"].append(d["_id"]); _idx["P"].append(p); _idx["A"].append(a); _idx["C"].append(c)
    _idx["meta"][d["_id"]] = {k: d.get(k) for k in ("name", "set_id", "set_name", "local_id", "image")}
    _idx["mat"] = None


def _matrix():
    if _idx["mat"] is None and _idx["ids"]:
        _idx["mat"] = (np.vstack(_idx["P"]), np.vstack(_idx["A"]), np.vstack(_idx["C"]))
    return _idx["mat"]


async def hash_card(db, c, set_id, set_name):
    if c["id"] in _idx["meta"] or not c.get("image"):
        return
    try:
        r = await tcgdex.http.get(f"{c['image']}/low.png")
        r.raise_for_status()
        p, a, col = await asyncio.to_thread(feats, Image.open(io.BytesIO(r.content)))
    except Exception:  # noqa
        status["errors"] += 1
        return
    d = {"_id": c["id"], "p": p, "a": a, "c": col, "name": c.get("name"), "set_id": set_id, "set_name": set_name,
         "local_id": c.get("localId"), "image": c.get("image")}
    await db.card_hashes.replace_one({"_id": c["id"]}, d, upsert=True)
    _add_mem(d)


async def build_index(db, set_ids=None):
    if status["running"]:
        return
    await load_index(db)
    sets = await tcgdex.all_sets(db)
    target = [s for s in sets if not set_ids or s["id"] in set_ids]
    status.update(running=True, done=0, total=len(target), errors=0, current=None)
    sem = asyncio.Semaphore(8)

    async def one(c, s):
        async with sem:
            await hash_card(db, c, s["id"], s["name"])
    try:
        for s in target:
            status["current"] = s["name"]
            try:
                sd = await tcgdex.get_set(db, s["id"])
                await asyncio.gather(*[one(c, s) for c in (sd or {}).get("cards", [])])
            except Exception as e:  # noqa
                log.warning("index set %s failed %s", s["id"], e)
                status["errors"] += 1
            status["done"] += 1
    finally:
        status["running"] = False
        status["current"] = None


def index_status():
    return {**status, "indexed": len(_idx["ids"])}


# ---------- recognition ----------
def _same_num(local_id, n):
    a, b = tcgdex.to_int(local_id), tcgdex.to_int(n)
    if a is not None and b is not None:
        return a == b
    return str(local_id).lstrip("0").upper() == str(n).lstrip("0").upper()


async def _cands_number(db, num, total, sets):
    out = []
    tot = tcgdex.to_int(total)
    if tot is None:
        res = await tcgdex.fetch(db, "/cards", {"localId": f"eq:{num}", "pagination:itemsPerPage": 50}) or []
        return res
    matching = [s for s in sets if (s.get("cardCount") or {}).get("official") == tot][:15]
    details = await asyncio.gather(*[tcgdex.get_set(db, s["id"]) for s in matching], return_exceptions=True)
    for sd in details:
        if isinstance(sd, dict):
            out += [c for c in sd.get("cards", []) if _same_num(c.get("localId"), num)]
    return out


async def recognize(db, data: bytes):
    await load_index(db)
    arr = np.frombuffer(data, np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return {"matches": [], "error": "Could not read image"}
    card, detected = await asyncio.to_thread(detect_card, bgr)
    flipped = cv2.rotate(card, cv2.ROTATE_180)
    ocr, llm = await asyncio.gather(asyncio.to_thread(ocr_info, card), ollama_read(data))
    if not ocr["numbers"]:
        o2 = await asyncio.to_thread(ocr_info, flipped)
        if o2["numbers"]:
            ocr, card, flipped = o2, flipped, card
    if llm:
        m = NUM_RE.search(str(llm.get("number") or ""))
        if m:
            ocr["numbers"].insert(0, m.groups())
        if llm.get("name"):
            ocr["words"].insert(0, str(llm["name"]))
    q = [_vec(*feats(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))) for img in (card, flipped)]

    sets = await tcgdex.all_sets(db)
    set_names = {s["id"]: s["name"] for s in sets}
    cands, num_ids = {}, set()
    for num, total in ocr["numbers"][:2]:
        for c in await _cands_number(db, num, total, sets):
            cands[c["id"]] = c
            num_ids.add(c["id"])
    if len(cands) < 3:
        for w in ocr["words"][:2]:
            res = await tcgdex.fetch(db, "/cards", {"name": w, "pagination:itemsPerPage": 60}) or []
            for c in res:
                cands.setdefault(c["id"], c)
    mat = _matrix()
    if mat is not None:
        d = np.minimum(_dist(*q[0], *mat), _dist(*q[1], *mat))
        for i in np.argsort(d)[:12]:
            cid = _idx["ids"][i]
            m = _idx["meta"][cid]
            cands.setdefault(cid, {"id": cid, "name": m["name"], "localId": m["local_id"], "image": m["image"]})
    missing = [c for cid, c in list(cands.items())[:60] if cid not in _idx["meta"]]
    sem = asyncio.Semaphore(10)

    async def h(c):
        async with sem:
            sid = c["id"].rsplit("-", 1)[0]
            await hash_card(db, c, sid, set_names.get(sid))
    await asyncio.gather(*[h(c) for c in missing])

    pocket = await tcgdex.fetch(db, "/series/tcgp", ttl=12 * 3600) or {}
    digital = {s["id"] for s in pocket.get("sets") or []}
    scored = []
    words = [w.lower() for w in ocr["words"]]
    for cid, c in cands.items():
        if cid not in _idx["meta"] or cid.rsplit("-", 1)[0] in digital:
            continue
        i = _idx["ids"].index(cid)
        P, A, C = _idx["P"][i][None], _idx["A"][i][None], _idx["C"][i][None]
        dist = float(min(_dist(*q[0], P, A, C)[0], _dist(*q[1], P, A, C)[0]))
        score = 1 - dist
        if cid in num_ids:
            score += 0.12
        cname = (c.get("name") or "").lower()
        if words:
            score += 0.10 * max(difflib.SequenceMatcher(None, w, cname.split(" ")[0]).ratio() for w in words)
        sid = cid.rsplit("-", 1)[0]
        scored.append({"card_id": cid, "name": c.get("name"), "local_id": c.get("localId"), "image": c.get("image"),
                       "set_id": sid, "set_name": set_names.get(sid), "score": round(score, 3),
                       "visual": round(1 - dist, 3), "number_match": cid in num_ids})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:6]
    for m in top[:3]:
        try:
            full = await tcgdex.get_card(db, m["card_id"])
            m["variants"] = tcgdex.variants_of(full)
            m.update(tcgdex.price_for(full, m["variants"][0]))
            m["set_total"] = ((full.get("set") or {}).get("cardCount") or {}).get("official")
        except Exception:  # noqa
            m["variants"] = ["normal"]
    conf = "none"
    if top:
        gap = top[0]["score"] - (top[1]["score"] if len(top) > 1 else 0.5)
        s = top[0]["score"]
        conf = "high" if (s > 0.85 and gap > 0.05) or (top[0]["number_match"] and gap > 0.08 and s > 0.75) else ("medium" if s > 0.7 else "low")
    return {"matches": top, "confidence": conf, "detected": detected,
            "ocr": {"numbers": ["/".join(n) for n in ocr["numbers"]], "words": ocr["words"]}}
