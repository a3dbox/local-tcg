import pytest

import tcgdex
import fakes


@pytest.fixture(autouse=True)
def fx():
    tcgdex.FX.update(eur_gbp=0.85, usd_gbp=0.85 / 1.10)
    yield


def test_to_int():
    assert tcgdex.to_int("007") == 7
    assert tcgdex.to_int("136") == 136
    assert tcgdex.to_int("TG12") is None
    assert tcgdex.to_int(None) is None


def test_variants_from_detailed_dict_and_default():
    assert tcgdex.variants_of(fakes.CARDS["tst1-2"]) == ["normal", "reverse"]
    assert tcgdex.variants_of(fakes.CARDS["tst1-1"]) == ["normal", "reverse"]
    assert tcgdex.variants_of({"variants_detailed": [{"type": "firstedition"}]}) == ["firstEdition"]
    assert tcgdex.variants_of({}) == ["normal"]


def test_price_prefers_cardmarket_for_gbp():
    p = tcgdex.price_for(fakes.CARDS["tst1-1"], "normal")
    assert p["price_usd"] == 1.0 and p["price_eur"] == 0.8
    assert p["price_gbp"] == pytest.approx(0.68, abs=0.01)


def test_price_holo_variants_use_holo_trend():
    p = tcgdex.price_for(fakes.CARDS["tst1-1"], "reverse")
    assert p["price_usd"] == 2.0 and p["price_eur"] == 1.5
    assert p["price_gbp"] == pytest.approx(1.275, abs=0.01)


def test_price_falls_back_to_usd_conversion_and_mid_price():
    p = tcgdex.price_for(fakes.CARDS["tst1-2"], "reverse")
    assert p["price_usd"] == 4.0 and p["price_eur"] is None
    assert p["price_gbp"] == pytest.approx(4.0 * 0.85 / 1.10, abs=0.01)


def test_price_missing_everything():
    assert tcgdex.price_for(fakes.CARDS["tst2-1"], "normal") == {"price_usd": None, "price_eur": None, "price_gbp": None}


def test_to_gbp_without_rates_returns_none():
    tcgdex.FX.update(eur_gbp=None, usd_gbp=None)
    assert tcgdex.to_gbp(1.0, 1.0) is None


async def test_refresh_fx_sets_rates():
    tcgdex.FX.update(eur_gbp=None, usd_gbp=None)
    await tcgdex.refresh_fx(None)
    assert tcgdex.FX["eur_gbp"] == 0.85
    assert tcgdex.FX["usd_gbp"] == pytest.approx(0.85 / 1.10)


def test_summarize():
    s = tcgdex.summarize(fakes.CARDS["tst1-3"])
    assert s["card_id"] == "tst1-3" and s["set_id"] == "tst1" and s["set_name"] == "Test Set"
    assert s["local_num"] == 3 and s["types"] == ["Lightning"]


def test_progress_base_full_master():
    sd = fakes.SETS["tst1"]
    p = tcgdex.progress(sd, {"tst1-1": {"normal": 1, "reverse": 2}, "tst1-3": {"holo": 1}})
    assert p["base"] == [1, 2]
    assert p["full"] == [2, 3]
    assert p["master"] == [3, 5]
    assert tcgdex.progress(sd, {})["full"] == [0, 3]


@pytest.mark.parametrize("sid,expected", [("sv08", "sv8"), ("sv03.5", "sv3pt5"), ("swsh3.5", "swsh35"),
                                          ("base1", "base1"), ("me01", "me1"), ("swsh3", "swsh3")])
def test_symbol_url_mapping(sid, expected):
    assert tcgdex.symbol_url(sid) == f"{tcgdex.SYMBOL_BASE}/{expected}/symbol.png"
