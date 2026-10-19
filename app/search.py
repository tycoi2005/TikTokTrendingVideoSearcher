"""Tìm kiếm video theo từ khóa trên tiktok.com bằng trình duyệt thật.

TikTok bảo vệ API tìm kiếm bằng chữ ký (X-Bogus / msToken) và captcha, nên
cách ổn định nhất là để trình duyệt tự tải trang tìm kiếm rồi đọc lại phản hồi
JSON của endpoint ``/api/search/general/full``.

Lưu ý:
  * TikTok thường CHẶN chế độ headless => mặc định mở cửa sổ Chrome
    (đặt ``HEADLESS=true`` nếu muốn chạy ẩn và chấp nhận rủi ro captcha).
  * Dùng *persistent context* để giữ cookie: chỉ cần giải captcha/đăng nhập
    một lần, các lần sau tái sử dụng phiên.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from . import config

_VIDEO_ID_RE = re.compile(r"/video/(\d+)")


class CaptchaError(RuntimeError):
    """TikTok yêu cầu xác minh (captcha)."""


class BrowserClosedError(RuntimeError):
    """Cửa sổ trình duyệt bị đóng giữa chừng (người dùng tự đóng)."""


_CLOSED_HINTS = (
    "has been closed",
    "target closed",
    "browser has been closed",
    "context has been closed",
    "connection closed",
)


def _is_closed_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(hint in msg for hint in _CLOSED_HINTS)


_CAPTCHA_SELECTOR = (
    "#captcha, .captcha_verify_container, .captcha-verify-container, "
    "iframe[src*='captcha'], iframe[src*='verify']"
)

_CAPTCHA_MESSAGE = (
    "TikTok đang yêu cầu xác minh (captcha). Cửa sổ Chrome đang mở — hãy giải "
    "captcha; app sẽ tự động tiếp tục khi xong (cookie được lưu cho lần sau). "
    "Nếu không thấy cửa sổ, hãy đặt HEADLESS=false trong .env và thử lại."
)


async def _is_captcha(page) -> bool:
    """Phát hiện captcha: chỉ dựa vào DOM/title (tránh dương tính giả)."""
    try:
        if await page.query_selector(_CAPTCHA_SELECTOR):
            return True
    except Exception:
        pass
    try:
        low = (await page.title() or "").lower()
    except Exception:
        return False
    return "captcha" in low or "xác minh" in low


def _extract_item(entry: dict, region: str | None, keyword: str) -> dict | None:
    if not isinstance(entry, dict) or entry.get("type") != 1:
        return None
    item = entry.get("item") or {}
    video_id = item.get("id")
    if not video_id:
        return None
    author = item.get("author") or {}
    stats = item.get("stats") or {}
    video = item.get("video") or {}
    handle = author.get("uniqueId")
    return {
        "id": str(video_id),
        "url": f"https://www.tiktok.com/@{handle}/video/{video_id}",
        "title": item.get("desc") or "",
        "cover": video.get("cover") or video.get("originCover"),
        "create_time": item.get("createTime"),
        "author": {
            "name": author.get("nickname"),
            "handle": handle,
            "avatar": author.get("avatarThumb"),
        },
        "stats": {
            "views": stats.get("playCount"),
            "likes": stats.get("diggCount"),
            "comments": stats.get("commentCount"),
            "shares": stats.get("shareCount"),
        },
        "region": (region or "").upper() or None,
        "keyword": keyword,
    }


def _parse_payloads(payloads: list[dict], region: str | None, keyword: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for payload in payloads:
        for entry in payload.get("item_list") or []:
            parsed = _extract_item(entry, region, keyword)
            if parsed and parsed["id"] not in seen:
                seen.add(parsed["id"])
                out.append(parsed)
    return out


_NUMERIC_ONLY_RE = re.compile(r"^[\d.,\s]+[KMBkmb]?$")


def _best_title(node: dict) -> str:
    """Chọn caption hợp lý nhất (bỏ qua các dòng chỉ là lượt xem dạng số)."""
    blocks: list[str] = []
    for key in ("aria", "title", "alt", "anchorText", "cardText"):
        if node.get(key):
            blocks.append(node[key])

    best = ""
    for block in blocks:
        for line in (block or "").split("\n"):
            line = line.strip()
            if len(line) < 4 or _NUMERIC_ONLY_RE.match(line):
                continue
            if sum(ch.isalpha() for ch in line) < 3:
                continue
            if len(line) > len(best):
                best = line
    return best


async def _extract_from_dom(page, region: str | None, keyword: str) -> list[dict]:
    """Phương án dự phòng: đọc các thẻ video đã render trong DOM."""
    try:
        raw = await page.eval_on_selector_all(
            "a[href*='/video/']",
            """els => els.map(a => {
                 const img = a.querySelector('img');
                 // Mở rộng ra "card" chứa đúng 1 video để lấy caption, tránh
                 // lấy text của cả lưới kết quả.
                 let card = a, p = a.parentElement;
                 while (p && p.querySelectorAll("a[href*='/video/']").length <= 1) {
                   card = p; p = p.parentElement;
                 }
                 return {
                   href: a.href,
                   img: img ? img.src : '',
                   alt: img ? (img.alt || '') : '',
                   aria: a.getAttribute('aria-label') || '',
                   title: a.getAttribute('title') || '',
                   anchorText: a.innerText || '',
                   cardText: card.innerText || '',
                 };
               })""",
        )
    except Exception:
        return []

    out: list[dict] = []
    seen: set[str] = set()
    for node in raw:
        match = _VIDEO_ID_RE.search(node.get("href") or "")
        if not match:
            continue
        video_id = match.group(1)
        if video_id in seen:
            continue
        seen.add(video_id)
        handle = None
        hm = re.search(r"tiktok\.com/@([^/]+)/video", node.get("href") or "")
        if hm:
            handle = hm.group(1)
        out.append(
            {
                "id": video_id,
                "url": node.get("href") or f"https://www.tiktok.com/video/{video_id}",
                "title": _best_title(node),
                "cover": node.get("img") or None,
                "create_time": None,
                "author": {"name": None, "handle": handle, "avatar": None},
                "stats": {
                    "views": None,
                    "likes": None,
                    "comments": None,
                    "shares": None,
                },
                "region": (region or "").upper() or None,
                "keyword": keyword,
            }
        )
    return out


class SearchBrowser:
    """Bọc một trình duyệt Playwright dùng chung cho mọi truy vấn tìm kiếm."""

    def __init__(self) -> None:
        self._pw = None
        self._ctx = None
        self._page = None
        self._payloads: list[dict] = []
        self._first_payload: asyncio.Event | None = None
        self._idle_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    def _context_alive(self) -> bool:
        if self._ctx is None:
            return False
        try:
            browser = self._ctx.browser
            if browser is not None and not browser.is_connected():
                return False
            _ = self._ctx.pages
            return True
        except Exception:
            return False

    async def _reset(self) -> None:
        ctx, pw = self._ctx, self._pw
        self._ctx = self._pw = self._page = None
        for resource in (ctx, pw):
            if resource is None:
                continue
            try:
                await (resource.close() if resource is ctx else resource.stop())
            except Exception:
                pass

    async def _handle_response(self, response) -> None:
        if "search/general/full" not in response.url:
            return
        try:
            data = await response.json()
        except Exception:
            return
        if data:
            self._payloads.append(data)
            if self._first_payload is not None:
                self._first_payload.set()

    async def _get_page(self):
        """Trả về 1 tab dùng lại cho mọi lần tìm (không mở/đóng tab mới)."""
        if self._page is not None and not self._page.is_closed():
            return self._page
        page = await self._ctx.new_page()
        page.on("response", lambda r: asyncio.create_task(self._handle_response(r)))
        self._page = page
        return page

    async def _close_blank_pages(self) -> None:
        """Đóng tab trống mặc định (about:blank / chrome://...) do Chrome tạo."""
        if self._ctx is None:
            return
        try:
            pages = list(self._ctx.pages)
        except Exception:
            return
        for pg in pages:
            try:
                url = pg.url or ""
                if url in ("", "about:blank") or url.startswith(
                    ("chrome://", "edge://", "devtools://")
                ):
                    await pg.close()
            except Exception:
                pass

    async def _ensure(self) -> None:
        if self._context_alive():
            return
        if self._ctx is not None or self._pw is not None:
            # Context cũ đã bị đóng (ví dụ người dùng đóng cửa sổ) => dựng lại.
            await self._reset()
        from playwright.async_api import async_playwright

        config.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._pw = await async_playwright().start()

        kwargs = {
            "user_data_dir": str(config.USER_DATA_DIR),
            "headless": config.HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--hide-crash-restore-bubble",
            ],
            "locale": "en-US",
            "viewport": {"width": 1280, "height": 800},
            "user_agent": config.HTTP_USER_AGENT,
        }
        try:
            self._ctx = await self._pw.chromium.launch_persistent_context(
                channel=config.BROWSER_CHANNEL, **kwargs
            )
        except Exception:
            kwargs.pop("channel", None)
            kwargs.pop("user_agent", None)
            self._ctx = await self._pw.chromium.launch_persistent_context(**kwargs)

        await self._ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        # Dọn tab trống để chỉ còn các tab tìm kiếm.
        await self._close_blank_pages()

    async def _collect(
        self, page, payloads: list[dict], region: str | None, keyword: str, limit: int
    ) -> list[dict]:
        # Đủ số lượng cần thì không cuộn/chờ thêm.
        items = _parse_payloads(payloads, region, keyword)
        for _ in range(config.SEARCH_SCROLLS):
            if len(items) >= limit:
                break
            await page.mouse.wheel(0, 1600)
            await page.wait_for_timeout(config.SEARCH_SCROLL_WAIT_MS)
            items = _parse_payloads(payloads, region, keyword)
        if not items:
            # Dự phòng khi không bắt được JSON: đọc video đã render trong DOM.
            items = await _extract_from_dom(page, region, keyword)
        return items

    async def search(
        self,
        keyword: str,
        region: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        if not keyword.strip():
            return []

        async with self._lock:
            self._cancel_idle_close()
            await self._ensure()
            url = f"https://www.tiktok.com/search?q={quote(keyword)}"
            self._payloads = []
            self._first_payload = asyncio.Event()
            payloads = self._payloads
            first_payload = self._first_payload

            try:
                page = await self._get_page()
                if not config.HEADLESS:
                    try:
                        await page.bring_to_front()
                    except Exception:
                        pass

                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=config.SEARCH_TIMEOUT_MS,
                )
                # Chờ phản hồi JSON đầu tiên (tối đa SEARCH_SETTLE_MS) thay vì
                # luôn ngủ cố định -> nhanh hơn khi kết quả về sớm.
                try:
                    await asyncio.wait_for(
                        first_payload.wait(), timeout=config.SEARCH_SETTLE_MS / 1000
                    )
                except Exception:
                    pass

                items = await self._collect(page, payloads, region, keyword, limit)

                # Chỉ coi là captcha khi có bằng chứng rõ ràng và chưa có video nào.
                if not items and await _is_captcha(page):
                    items = await self._wait_for_captcha(
                        page, payloads, url, region, keyword, limit
                    )

                if not items:
                    if await _is_captcha(page):
                        raise CaptchaError(_CAPTCHA_MESSAGE)
                    raise CaptchaError(
                        "TikTok không trả về kết quả cho phiên này (có thể bị chặn "
                        "tạm thời hoặc tài khoản bị hạn chế). Thử lại sau ít phút, "
                        "hoặc đổi mạng/IP."
                    )
                return items[:limit]
            except Exception as exc:
                if _is_closed_error(exc):
                    await self._reset()
                    raise BrowserClosedError(
                        "Cửa sổ trình duyệt đã bị đóng giữa chừng. App sẽ tự mở lại "
                        "ở lần tìm kiếm tiếp theo."
                    ) from exc
                raise
            finally:
                self._first_payload = None
                self._schedule_idle_close()

    async def _wait_for_captcha(
        self,
        page,
        payloads: list[dict],
        url: str,
        region: str | None,
        keyword: str,
        limit: int,
    ) -> list[dict]:
        """Giữ cửa sổ cho người dùng giải captcha; poll kết quả đến khi xong."""
        if config.HEADLESS or config.CAPTCHA_WAIT_SECONDS <= 0:
            raise CaptchaError(_CAPTCHA_MESSAGE)

        try:
            await page.bring_to_front()
        except Exception:
            pass

        deadline = asyncio.get_event_loop().time() + config.CAPTCHA_WAIT_SECONDS
        reload_every = 10.0
        last_reload = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() < deadline:
            await page.wait_for_timeout(3000)

            items = _parse_payloads(payloads, region, keyword)
            if not items:
                items = await _extract_from_dom(page, region, keyword)
            if items:
                return items

            if not await _is_captcha(page):
                # Đã giải xong nhưng chưa có dữ liệu => nạp lại trang tìm kiếm.
                now = asyncio.get_event_loop().time()
                if now - last_reload >= reload_every:
                    last_reload = now
                    try:
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=config.SEARCH_TIMEOUT_MS,
                        )
                        await page.wait_for_timeout(config.SEARCH_SETTLE_MS)
                        items = await self._collect(
                            page, payloads, region, keyword, limit
                        )
                        if items:
                            return items
                    except Exception:
                        pass

        raise CaptchaError(
            f"Hết thời gian chờ giải captcha ({config.CAPTCHA_WAIT_SECONDS}s). "
            "Hãy thử lại và giải captcha trong cửa sổ trình duyệt."
        )

    async def _idle_close(self, seconds: float) -> None:
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        # Chỉ đóng nếu không có tìm kiếm mới xen vào (lock còn trống).
        if self._lock.locked():
            return
        await self._reset()

    def _cancel_idle_close(self) -> None:
        task = self._idle_task
        self._idle_task = None
        if task is not None and not task.done():
            task.cancel()

    def _schedule_idle_close(self) -> None:
        seconds = config.BROWSER_IDLE_CLOSE_SECONDS
        self._cancel_idle_close()
        if seconds > 0 and (self._ctx is not None):
            self._idle_task = asyncio.create_task(self._idle_close(seconds))

    async def close(self) -> None:
        self._cancel_idle_close()
        await self._reset()


search_browser = SearchBrowser()
