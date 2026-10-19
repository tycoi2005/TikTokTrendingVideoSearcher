"""Dịch thuật miễn phí qua endpoint công khai của Google Translate.

Không cần API key. Dùng cho 2 việc:
  * dịch TỪ KHÓA đầu vào sang ngôn ngữ đích trước khi tìm kiếm, và
  * dịch TIÊU ĐỀ video kết quả về ngôn ngữ người dùng.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

import httpx

from . import config

_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_cache: dict[tuple[str, str, str], str] = {}


async def translate(
    client: httpx.AsyncClient,
    text: str,
    dest: str,
    source: str = "auto",
) -> str:
    """Dịch ``text`` sang ``dest``; trả về nguyên bản nếu lỗi."""
    text = (text or "").strip()
    if not text or not dest:
        return text
    if source != "auto" and source == dest:
        return text

    key = (text, source, dest)
    if key in _cache:
        return _cache[key]

    params = {"client": "gtx", "sl": source, "tl": dest, "dt": "t", "q": text}
    try:
        resp = await client.get(_ENDPOINT, params=params)
        resp.raise_for_status()
        payload = resp.json()
        translated = "".join(seg[0] for seg in payload[0] if seg and seg[0])
        translated = translated or text
    except Exception:
        translated = text

    _cache[key] = translated
    return translated


async def translate_many(
    texts: Iterable[str],
    dest: str,
    source: str = "auto",
) -> list[str]:
    """Dịch nhiều đoạn văn bản, giới hạn số request đồng thời."""
    items = list(texts)
    if not items:
        return []

    sem = asyncio.Semaphore(6)
    limits = httpx.Limits(max_connections=8)
    timeout = httpx.Timeout(config.TRANSLATE_TIMEOUT)

    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, headers={"User-Agent": config.HTTP_USER_AGENT}
    ) as client:

        async def _one(value: str) -> str:
            async with sem:
                return await translate(client, value, dest, source)

        return list(await asyncio.gather(*(_one(t) for t in items)))
