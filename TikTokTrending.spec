# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: đóng gói app thành thư mục chạy trên Windows.

Build:  pyinstaller --clean --noconfirm TikTokTrending.spec
Yêu cầu: đã chạy `set PLAYWRIGHT_BROWSERS_PATH=0` + `python -m playwright install chromium`
         TRƯỚC khi build (xem build_windows.bat).
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

datas = [(str(ROOT / "static"), "static")]
binaries = []
hiddenimports = []

# Playwright: gói cả driver (node) lẫn Chromium đã tải vào gói.
for package in ("playwright",):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += collect_submodules("uvicorn")

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TikTokTrending",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TikTokTrending",
)
