"""Dịch thuật miễn phí qua endpoint công khai của Google Translate.

Không cần API key. Dùng cho 2 việc:
  * dịch TỪ KHÓA đầu vào sang ngôn ngữ đích trước khi tìm kiếm, và
  * dịch TIÊU ĐỀ video kết quả về ngôn ngữ người dùng.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import httpx

from . import config

logger = logging.getLogger(__name__)

_ENDPOINT_PRIMARY = "https://translate.googleapis.com/translate_a/single"
_ENDPOINT_SECONDARY = "https://clients5.google.com/translate_a/t"
_ENDPOINT_MYMEMORY = "https://api.mymemory.translated.net/get"

_cache: dict[tuple[str, str, str], str] = {}


async def _try_google_single(
    client: httpx.AsyncClient, text: str, dest: str, source: str
) -> str | None:
    params = {"client": "dict-chrome-ex", "sl": source, "tl": dest, "dt": "t", "q": text}
    resp = await client.get(_ENDPOINT_PRIMARY, params=params)
    if resp.status_code == 200:
        payload = resp.json()
        if payload and isinstance(payload, list) and payload[0]:
            translated = "".join(seg[0] for seg in payload[0] if seg and seg[0])
            if translated:
                return translated
    return None


async def _try_google_clients5(
    client: httpx.AsyncClient, text: str, dest: str, source: str
) -> str | None:
    params = {"client": "dict-chrome-ex", "sl": source, "tl": dest, "q": text}
    resp = await client.get(_ENDPOINT_SECONDARY, params=params)
    if resp.status_code == 200:
        payload = resp.json()
        if isinstance(payload, list) and payload:
            item = payload[0]
            if isinstance(item, list) and item:
                return str(item[0])
            elif isinstance(item, str):
                return item
    return None


async def _try_mymemory(
    client: httpx.AsyncClient, text: str, dest: str, source: str
) -> str | None:
    langpair = f"{source}|{dest}" if source != "auto" else f"autodetect|{dest}"
    params = {"q": text, "langpair": langpair}
    resp = await client.get(_ENDPOINT_MYMEMORY, params=params)
    if resp.status_code == 200:
        data = resp.json()
        trans = data.get("responseData", {}).get("translatedText")
        if trans and "MYMEMORY WARNING" not in trans:
            return trans
    return None


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

    translated = None
    for attempt in (_try_google_single, _try_google_clients5, _try_mymemory):
        try:
            translated = await attempt(client, text, dest, source)
            if translated:
                break
        except Exception as exc:
            logger.debug("Translation attempt failed: %s", exc)

    translated = translated or text
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
