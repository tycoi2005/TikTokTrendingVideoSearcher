"""Trình khởi chạy app: mở server local rồi tự mở trình duyệt.

Chạy trực tiếp:  python run.py
Bản đóng gói (Windows):  dist\\TikTokTrending\\TikTokTrending.exe
"""
from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import threading
import webbrowser


def _prepare_env() -> None:
    """Thiết lập môi trường đặc thù cho bản đóng gói."""
    if getattr(sys, "frozen", False):
        # Chromium được bundle ngay trong gói Playwright.
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")


def _free_port(preferred: int) -> int:
    """Tìm cổng trống, ưu tiên `preferred` rồi các cổng kế tiếp."""
    for port in [preferred, *range(preferred + 1, preferred + 20)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _resolve_port() -> int:
    env_port = (os.getenv("PORT") or "").strip()
    if env_port:
        return int(env_port)
    from app import config

    return _free_port(config.PORT)


def main() -> None:
    _prepare_env()
    multiprocessing.freeze_support()

    import uvicorn

    from app import config
    from app.main import app as fastapi_app

    port = _resolve_port()
    url = f"http://{config.HOST}:{port}"

    if os.getenv("OPEN_BROWSER", "1").strip().lower() not in {"0", "false", "no"}:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print(f"\n  TikTok Trending & Search đang chạy tại: {url}\n")
    if config.DATA_DIR != config.BASE_DIR:
        print(f"  Dữ liệu (profile trình duyệt, .env): {config.DATA_DIR}\n")
    print("  Đóng cửa sổ này để tắt app.\n")

    uvicorn.run(fastapi_app, host=config.HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
