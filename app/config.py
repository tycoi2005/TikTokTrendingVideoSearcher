"""Cấu hình ứng dụng (đọc từ file .env và biến môi trường, có giá trị mặc định)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Thư mục gốc mã nguồn (khi chạy trực tiếp từ source).
BASE_DIR = Path(__file__).resolve().parent.parent


def _is_frozen() -> bool:
    """True khi chạy bản đã đóng gói (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    """Nơi chứa tài nguyên chỉ đọc (ví dụ `static/`)."""
    if _is_frozen():
        # One-folder: PyInstaller 6 đặt mọi thứ trong `_internal` (_MEIPASS).
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return BASE_DIR


def _default_data_dir() -> Path:
    """Nơi ghi dữ liệu (profile trình duyệt, .env, cache).

    Khi đóng gói, dùng `%LOCALAPPDATA%\\TikTokTrending` để không ghi cạnh .exe
    (tránh lỗi quyền và mất dữ liệu khi cập nhật).
    """
    if _is_frozen():
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if not base:
            base = str(Path.home() / ".tiktok-trending")
        return Path(base) / "TikTokTrending"
    return BASE_DIR


RESOURCE_DIR = _resource_dir()
DATA_DIR = Path(os.getenv("DATA_DIR", str(_default_data_dir()))).expanduser()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass


def _apply_dotenv(env_path: Path) -> None:
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


def _load_dotenv() -> None:
    """Nạp file .env (nếu có) mà KHÔNG ghi đè biến môi trường đã tồn tại.

    Ưu tiên .env trong thư mục dữ liệu, sau đó tới thư mục mã nguồn.
    """
    for env_path in (DATA_DIR / ".env", BASE_DIR / ".env"):
        if env_path.exists():
            _apply_dotenv(env_path)


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
# "chrome" dùng Chrome cài sẵn; để trống ("") dùng Chromium đi kèm Playwright.
# Bản đóng gói đi kèm Chromium nên mặc định để trống.
BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "" if _is_frozen() else "chrome")
_raw_user_data_dir = Path(
    os.getenv("USER_DATA_DIR", str(DATA_DIR / ".browser-profile"))
).expanduser()
USER_DATA_DIR = (
    _raw_user_data_dir if _raw_user_data_dir.is_absolute() else DATA_DIR / _raw_user_data_dir
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
