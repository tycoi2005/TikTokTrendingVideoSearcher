@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Build TikTok Trending ^& Search cho Windows
echo ============================================================
echo.

where python >nul 2>nul || (echo [LOI] Khong tim thay Python. Cai Python 3.10+ roi chay lai. & exit /b 1)

echo [1/4] Tao moi truong ao .venv ...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv || (echo [LOI] Tao venv that bai. & exit /b 1)
)
call ".venv\Scripts\activate.bat" || (echo [LOI] Kich hoat venv that bai. & exit /b 1)

echo [2/4] Cai thu vien ...
python -m pip install --upgrade pip >nul || (echo [LOI] Nang cap pip that bai. & exit /b 1)
pip install -r requirements.txt || (echo [LOI] Cai requirements that bai. & exit /b 1)
pip install "pyinstaller>=6.0" || (echo [LOI] Cai pyinstaller that bai. & exit /b 1)

echo [3/4] Tai Chromium (bundle vao app) ...
set PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium || (echo [LOI] Tai Chromium that bai. & exit /b 1)

echo [4/4] Dong goi bang PyInstaller ...
pyinstaller --clean --noconfirm TikTokTrending.spec || (echo [LOI] Build that bai. & exit /b 1)

echo.
echo ============================================================
echo   XONG!  App: dist\TikTokTrending\TikTokTrending.exe
echo   Chay file .exe de mo app (tu mo trinh duyet).
echo ============================================================
endlocal
