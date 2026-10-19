"""Lấy danh sách video trending từ TikTok Creative Center.

Đây là API công khai (không cần đăng nhập) mà trang
https://ads.tiktok.com/creative/creativeCenter/trends sử dụng.

- Bảng xếp hạng "Top Contents" hiện hỗ trợ các quốc gia trong
  :data:`app.countries.TRENDING_COUNTRIES` (VN, US, JP, TH, ID).
- Không cần cookie/chữ ký; chỉ cần User-Agent và Referer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from . import config
from .countries import TRENDING_COUNTRIES

_OVERVIEW_URL = "https://ads.us.tiktok.com/CreativeOne/Report/GetTopContentsOverview"
_LIST_PATH = "/CreativeOne/Report/CreativeCenterGetTopContentsList"

# period -> (periodDimension, khoá timestamp trong overview)
PERIODS: dict[str, tuple[int, str]] = {
    "24h": (3, "lastDailyEndTimestamp"),
    "7d": (1, "lastWeeklyEndTimestamp"),
    "30d": (2, "lastMonthlyEndTimestamp"),
}

_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "referer": "https://ads.tiktok.com/",
}


def _host(country: str) -> str:
    return "ads.us.tiktok.com" if country.upper() == "US" else "ads.tiktok.com"


async def _get_overview(client: httpx.AsyncClient) -> dict:
    resp = await client.get(_OVERVIEW_URL, headers=_HEADERS)
    resp.raise_for_status()
    return resp.json()


def _normalize(entity: dict, country: str, period: str) -> dict:
    info = entity.get("itemInfo") or {}
    author = entity.get("itemAuthorInfo") or {}
    author_metrics = entity.get("itemAuthorMetrics") or {}
    metrics = entity.get("itemMetrics") or {}

    item_id = info.get("itemID")
    return {
        "id": str(item_id) if item_id is not None else None,
        "url": f"https://www.tiktok.com/@{author.get('handlerName') or '_'}/video/{item_id}"
        if item_id
        else None,
        "title": info.get("title") or "",
        "cover": info.get("coverURL"),
        "video_url": info.get("videoURL"),
        "create_time": info.get("createTime"),
        "author": {
            "name": author.get("nickName"),
            "handle": author.get("handlerName"),
            "avatar": author.get("avatarURI"),
            "followers": _as_int(author_metrics.get("followers")),
        },
        "stats": {
            "views": _as_int(metrics.get("organicVideoViews")),
            "views_lifetime": _as_int(metrics.get("organicVideoViewsLifeTime")),
            "engagement_rate": metrics.get("engagementRate"),
            "six_seconds_vtr": metrics.get("sixSecondsVTR"),
        },
        "country": country.upper(),
        "period": period,
    }


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def fetch_trending(
    country: str,
    period: str = "7d",
    timeout: float | None = None,
) -> dict:
    """Trả về {'country', 'period', 'generated_at', 'items': [...]}."""
    country = country.upper()
    if country not in TRENDING_COUNTRIES:
        raise ValueError(
            f"TikTok chỉ hỗ trợ trending cho: {', '.join(TRENDING_COUNTRIES)}"
        )
    if period not in PERIODS:
        raise ValueError(f"period phải là một trong: {', '.join(PERIODS)}")

    dimension, ts_key = PERIODS[period]
    timeout = timeout or config.HTTP_TIMEOUT

    async with httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": config.HTTP_USER_AGENT}
    ) as client:
        overview = await _get_overview(client)
        end_ts = overview.get(ts_key)
        if not end_ts:
            raise RuntimeError("Không lấy được mốc thời gian từ Creative Center")

        params = {
            "contentLabelIDs": "",
            "countryCode": country,
            "limit": 50,
            "orderByMetric": 1,
            "organicOnly": "false",
            "page": 1,
            "periodDimension": dimension,
            "periodEndTimestamp": end_ts,
        }
        url = f"https://{_host(country)}{_LIST_PATH}"
        resp = await client.get(url, params=params, headers=_HEADERS)
        resp.raise_for_status()
        payload = resp.json()

    status = (payload.get("BaseResp") or {}).get("StatusCode")
    if status not in (0, None):
        raise RuntimeError(
            (payload.get("BaseResp") or {}).get("StatusMessage") or "Lỗi API"
        )

    items = [
        _normalize(e, country, period) for e in (payload.get("entityInfos") or [])
    ]

    return {
        "country": country,
        "country_name": TRENDING_COUNTRIES[country],
        "period": period,
        "period_end": end_ts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
