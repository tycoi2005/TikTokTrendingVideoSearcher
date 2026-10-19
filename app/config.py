"""Cấu hình ứng dụng (đọc từ file .env và biến môi trường, có giá trị mặc định)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Nạp file .env (nếu có) mà KHÔNG ghi đè biến môi trường đã tồn tại.

    Dùng python-dotenv nếu đã cài; nếu không, dùng bộ đọc tối giản.
    """
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# HTTP
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "25"))
HTTP_USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
)

# Trình duyệt dùng cho tìm kiếm từ khóa trên tiktok.com.
# TikTok thường chặn chế độ headless => mặc định mở cửa sổ (headless=False).
HEADLESS = _bool("HEADLESS", False)
BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "chrome")  # "chrome" | "chromium"
_raw_user_data_dir = Path(
    os.getenv("USER_DATA_DIR", str(BASE_DIR / ".browser-profile"))
).expanduser()
USER_DATA_DIR = (
    _raw_user_data_dir if _raw_user_data_dir.is_absolute() else BASE_DIR / _raw_user_data_dir
)
SEARCH_TIMEOUT_MS = int(os.getenv("SEARCH_TIMEOUT_MS", "30000"))
SEARCH_SETTLE_MS = int(os.getenv("SEARCH_SETTLE_MS", "3000"))
# Cuộn thêm tối đa bao nhiêu lần nếu chưa đủ số video yêu cầu.
SEARCH_SCROLLS = int(os.getenv("SEARCH_SCROLLS", "2"))
SEARCH_SCROLL_WAIT_MS = int(os.getenv("SEARCH_SCROLL_WAIT_MS", "1200"))
# Khi gặp captcha: giữ cửa sổ mở và chờ tối đa bao nhiêu giây để người dùng giải.
# Đặt 0 để tắt (báo lỗi ngay).
CAPTCHA_WAIT_SECONDS = int(os.getenv("CAPTCHA_WAIT_SECONDS", "180"))
# Tự đóng cửa sổ trình duyệt sau khi xong việc (không có tìm kiếm mới trong
# bao nhiêu giây). 0 = giữ cửa sổ luôn mở.
BROWSER_IDLE_CLOSE_SECONDS = float(os.getenv("BROWSER_IDLE_CLOSE_SECONDS", "5"))

# Dịch thuật
TRANSLATE_TIMEOUT = float(os.getenv("TRANSLATE_TIMEOUT", "15"))
DEFAULT_TARGET_LANG = os.getenv("DEFAULT_TARGET_LANG", "vi")
