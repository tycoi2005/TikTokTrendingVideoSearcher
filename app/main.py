"""Web app: xem video trending TikTok & tìm kiếm video theo từ khóa đa quốc gia.

Chạy:  uvicorn app.main:app --reload
Rồi mở http://127.0.0.1:8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, trending
from .countries import (
    COUNTRIES,
    LANGUAGE_NAMES,
    TRENDING_COUNTRIES,
    languages_for_countries,
)
from .search import BrowserClosedError, CaptchaError, search_browser
from .translate import translate, translate_many

STATIC_DIR = config.RESOURCE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await search_browser.close()


app = FastAPI(title="LinhLaGreen TikTok Search", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #
@app.get("/api/countries")
async def api_countries() -> dict:
    return {
        "trending": [
            {"code": code, "name": name}
            for code, name in TRENDING_COUNTRIES.items()
        ],
        "search": [
            {
                "code": code,
                "name": info["name"],
                "languages": [
                    {"code": lang, "name": LANGUAGE_NAMES.get(lang, lang)}
                    for lang in info["languages"]
                ],
            }
            for code, info in COUNTRIES.items()
        ],
        "languages": [
            {"code": code, "name": name} for code, name in LANGUAGE_NAMES.items()
        ],
    }


# --------------------------------------------------------------------------- #
# Trending
# --------------------------------------------------------------------------- #
@app.get("/api/trending")
async def api_trending(
    country: str = Query("VN", description="Mã quốc gia, ví dụ VN, US, JP, TH, ID"),
    period: str = Query("7d", description="24h | 7d | 30d"),
    translate: bool = Query(True, description="Dịch tiêu đề về target_lang"),
    target_lang: str = Query(config.DEFAULT_TARGET_LANG),
) -> dict:
    try:
        data = await trending.fetch_trending(country, period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi lấy dữ liệu: {exc}")

    if translate and data["items"]:
        titles = [item["title"] for item in data["items"]]
        translated = await translate_many(titles, target_lang)
        for item, text in zip(data["items"], translated):
            item["title_translated"] = text

    return data


# --------------------------------------------------------------------------- #
# Keyword search
# --------------------------------------------------------------------------- #
def _build_pairs(
    countries: list[str], languages: list[str]
) -> list[tuple[str, str]]:
    """Ghép (country, language) cần tìm kiếm, không trùng."""
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(country: str, lang: str) -> None:
        key = (country, lang)
        if key not in seen:
            seen.add(key)
            pairs.append(key)

    if languages:
        for lang in languages:
            matched = [
                c
                for c in countries
                if lang in COUNTRIES.get(c, {}).get("languages", [])
            ]
            for country in matched or (countries[:1] if countries else []):
                add(country, lang)
    else:
        for country in countries:
            for lang in COUNTRIES.get(country, {}).get("languages", ["en"]):
                add(country, lang)
    return pairs


@app.get("/api/search")
async def api_search(
    keyword: str = Query(..., min_length=1, description="Từ khóa nguồn, ví dụ 'khoai tây'"),
    countries: str = Query("", description="Danh sách mã quốc gia, phân tách bằng dấu phẩy"),
    languages: str = Query("", description="Danh sách mã ngôn ngữ, phân tách bằng dấu phẩy"),
    translate: bool = Query(True, description="Tự dịch từ khóa & tiêu đề"),
    target_lang: str = Query(config.DEFAULT_TARGET_LANG),
    limit: int = Query(3, ge=1, le=50, description="Số video tối đa mỗi nhóm"),
) -> dict:
    country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
    lang_list = [l.strip().lower() for l in languages.split(",") if l.strip()]
    if not country_list:
        country_list = ["VN"]

    pairs = _build_pairs(country_list, lang_list)
    if len(pairs) > 8:
        pairs = pairs[:8]
    if not pairs:
        raise HTTPException(status_code=400, detail="Không có cặp quốc gia/ngôn ngữ hợp lệ")

    groups = []
    aborted: str | None = None
    for country, lang in pairs:
        used_keyword = keyword
        if translate and lang:
            used_keyword = await _translate_keyword(keyword, lang)

        try:
            items = await search_browser.search(used_keyword, region=country, limit=limit)
        except CaptchaError as exc:
            # Dừng cả batch: đã cho người dùng thời gian giải captcha mà chưa xong,
            # chạy tiếp các ngôn ngữ khác cũng sẽ gặp captcha tương tự.
            groups.append(
                {"country": country, "language": lang, "keyword": used_keyword,
                 "search_url": f"https://www.tiktok.com/search?q={quote(used_keyword)}",
                 "error": str(exc), "items": []}
            )
            aborted = str(exc)
            break
        except BrowserClosedError as exc:
            # Cửa sổ bị đóng; context đã được dựng lại cho lần sau. Ghi chú & tiếp tục.
            groups.append(
                {"country": country, "language": lang, "keyword": used_keyword,
                 "search_url": f"https://www.tiktok.com/search?q={quote(used_keyword)}",
                 "error": str(exc), "items": []}
            )
            continue
        except Exception as exc:  # noqa: BLE001
            groups.append(
                {"country": country, "language": lang, "keyword": used_keyword,
                 "search_url": f"https://www.tiktok.com/search?q={quote(used_keyword)}",
                 "error": str(exc), "items": []}
            )
            continue

        for item in items:
            item["language"] = lang
        groups.append(
            {
                "country": country,
                "country_name": COUNTRIES.get(country, {}).get("name", country),
                "language": lang,
                "language_name": LANGUAGE_NAMES.get(lang, lang),
                "keyword": used_keyword,
                "search_url": f"https://www.tiktok.com/search?q={quote(used_keyword)}",
                "items": items,
            }
        )

    skipped = pairs[len(groups):]
    result = {"keyword": keyword, "target_lang": target_lang, "groups": groups}
    if aborted:
        result["hint"] = aborted
    if skipped:
        result["skipped"] = [
            {"country": c, "language": l} for c, l in skipped
        ]
    if translate:
        await _translate_groups(groups, target_lang)
    return result


async def _translate_keyword(keyword: str, lang: str) -> str:
    import httpx

    async with httpx.AsyncClient(
        timeout=config.TRANSLATE_TIMEOUT, headers={"User-Agent": config.HTTP_USER_AGENT}
    ) as client:
        return await translate(client, keyword, lang)


async def _translate_groups(groups: list[dict], target_lang: str) -> None:
    for group in groups:
        titles = [item["title"] for item in group.get("items", [])]
        if not titles:
            continue
        translated = await translate_many(titles, target_lang)
        for item, text in zip(group["items"], translated):
            item["title_translated"] = text


# --------------------------------------------------------------------------- #
# Static frontend
# --------------------------------------------------------------------------- #
@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
