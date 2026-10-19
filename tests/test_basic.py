"""Kiểm thử nhanh (chạy: python -m pytest -q hoặc python tests/test_basic.py)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.countries import COUNTRIES, TRENDING_COUNTRIES, languages_for_countries
from app.search import _best_title
from app.trending import PERIODS, _host, _normalize


def test_host_selection() -> None:
    assert _host("US") == "ads.us.tiktok.com"
    assert _host("vn") == "ads.tiktok.com"


def test_periods_defined() -> None:
    assert set(PERIODS) == {"24h", "7d", "30d"}


def test_languages_for_countries() -> None:
    assert languages_for_countries(["VN"]) == ["vi"]
    assert languages_for_countries(["US", "TH"]) == ["en", "th"]
    # không trùng lặp
    assert languages_for_countries(["US", "GB"]) == ["en"]


def test_normalize_schema() -> None:
    entity = {
        "itemInfo": {"itemID": 123, "title": "hi", "coverURL": "c"},
        "itemAuthorInfo": {"nickName": "N", "handlerName": "h"},
        "itemAuthorMetrics": {"followers": "10"},
        "itemMetrics": {"organicVideoViews": 5},
    }
    out = _normalize(entity, "vn", "7d")
    assert out["id"] == "123"
    assert out["country"] == "VN"
    assert out["author"]["followers"] == 10
    assert out["stats"]["views"] == 5
    assert out["url"].endswith("/video/123")


def test_trending_countries_supported() -> None:
    for code in TRENDING_COUNTRIES:
        assert code in COUNTRIES


def test_best_title_skips_numbers() -> None:
    assert _best_title({"aria": "", "anchorText": "6894"}) == ""
    assert _best_title({"cardText": "6.8K\nCách muối dưa leo"}) == "Cách muối dưa leo"
    assert _best_title({"alt": "dưa leo giòn ngon"}) == "dưa leo giòn ngon"


async def _live_smoke() -> None:
    from app.trending import fetch_trending

    data = await fetch_trending("VN", "7d")
    assert data["country"] == "VN"
    assert isinstance(data["items"], list)


if __name__ == "__main__":
    test_host_selection()
    test_periods_defined()
    test_languages_for_countries()
    test_normalize_schema()
    test_trending_countries_supported()
    asyncio.run(_live_smoke())
    print("OK")
