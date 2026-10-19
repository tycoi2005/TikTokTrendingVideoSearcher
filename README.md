# LinhLaGreen TikTok Search

Web app nhỏ để:

1. **Xem video trending TikTok** theo quốc gia (Việt Nam / toàn cầu) — khoảng 24 giờ, 7 ngày, 30 ngày.
2. **Tìm kiếm video theo từ khóa ở nhiều quốc gia / nhiều ngôn ngữ**.
3. **Tự động dịch**: dịch từ khóa đầu vào sang ngôn ngữ đích trước khi tìm kiếm, và dịch tiêu đề kết quả trở lại tiếng Việt (hoặc ngôn ngữ bạn chọn).

Ví dụ: từ khóa `khoai tây` → tự dịch thành `potato` (English) và `มันฝรั่ง` (Thai), tìm ở US / TH, rồi dịch tiêu đề kết quả về tiếng Việt.

## Nguồn dữ liệu

| Tính năng        | Nguồn                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Trending         | API công khai của **TikTok Creative Center** (không cần đăng nhập)     |
| Tìm kiếm từ khóa | **tiktok.com** qua trình duyệt thật (Playwright) đọc lại JSON tìm kiếm |
| Dịch thuật       | Endpoint miễn phí của Google Translate                                 |

**Trending hiện chỉ được TikTok hỗ trợ cho 5 quốc gia: `VN`, `US`, `JP`, `TH`, `ID`.**

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Trình duyệt: ưu tiên dùng Google Chrome đã cài (channel="chrome").
# Nếu chưa có Chrome, cài Chromium của Playwright:
playwright install chromium
```

## Chạy

```bash
python run.py            # mở server 127.0.0.1:8000 rồi tự mở trình duyệt
```

Hoặc dùng uvicorn trực tiếp:

```bash
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000

## Chạy trên Windows (đóng gói thành .exe)

Cần **Python 3.10+** trên Windows. Chỉ cần chạy:

```bat
build_windows.bat
```

Script sẽ tạo `.venv`, cài thư viện, tải Chromium (bundle vào app) và đóng gói
bằng PyInstaller. Kết quả:

```
dist\TikTokTrending\TikTokTrending.exe
```

Double-click file `.exe` để mở app (tự mở trình duyệt). Đóng cửa sổ console để tắt app.

Ghi chú khi đóng gói:

- Bản đóng gói **đi kèm Chromium** (`BROWSER_CHANNEL` trống) nên không cần cài Chrome.
- Dữ liệu (`profile trình duyệt`, `.env`) được ghi vào
  `%LOCALAPPDATA%\TikTokTrending`, không nằm cạnh file `.exe`.
- Thư mục `dist\TikTokTrending` có thể copy sang máy Windows khác (cùng kiến trúc).

## Biến môi trường

Cách đơn giản nhất là copy `.env.example` thành `.env` rồi chỉnh:

```bash
cp .env.example .env
```

Ví dụ muốn luôn thấy cửa sổ trình duyệt:

```env
HEADLESS=false
BROWSER_CHANNEL=chrome
```

App tự nạp `.env` lúc khởi động (biến môi trường thật trong shell vẫn được ưu tiên hơn `.env`).

| Biến               | Mặc định          | Ý nghĩa                                                       |
| ------------------ | ----------------- | ------------------------------------------------------------- |
| `HEADLESS`         | `false`           | Chạy trình duyệt ẩn. TikTok hay chặn headless → nên để `false`. |
| `BROWSER_CHANNEL`  | `chrome`          | `chrome` hoặc `chromium`. Bản đóng gói để trống → dùng Chromium đi kèm. |
| `USER_DATA_DIR`    | `.browser-profile`| Nơi lưu cookie (chỉ cần giải captcha 1 lần).                   |
| `DATA_DIR`         | `%LOCALAPPDATA%\TikTokTrending` (khi đóng gói) | Nơi ghi dữ liệu & nạp `.env`. |
| `CAPTCHA_WAIT_SECONDS` | `180`         | Khi gặp captcha, giữ cửa sổ mở và chờ bạn giải trong bao lâu. `0` = tắt. |
| `BROWSER_IDLE_CLOSE_SECONDS` | `5`      | Tự đóng cửa sổ trình duyệt sau khi xong việc bấy nhiêu giây. `0` = giữ mở. |
| `SEARCH_SCROLLS`   | `2`               | Số lần cuộn thêm nếu chưa đủ số video yêu cầu.                 |
| `SEARCH_SCROLL_WAIT_MS` | `1200`       | Thời gian chờ mỗi lần cuộn.                                    |
| `DEFAULT_TARGET_LANG` | `vi`           | Ngôn ngữ đích mặc định khi dịch.                              |

## API

- `GET /api/countries` — danh sách quốc gia / ngôn ngữ.
- `GET /api/trending?country=VN&period=7d&translate=true&target_lang=vi`
- `GET /api/search?keyword=khoai%20tây&countries=US,TH&languages=en,th&translate=true&target_lang=vi&limit=3`
  - `limit` = số video tối đa mỗi nhóm (mặc định `3`); đủ số lượng là dừng và chuyển nhóm kế tiếp.

## Lưu ý về tìm kiếm từ khóa

TikTok bảo vệ API tìm kiếm bằng chữ ký (X-Bogus / msToken) và captcha. App dùng
trình duyệt thật để vượt qua:

- Mặc định app **mở cửa sổ Chrome**. Khi TikTok hiện captcha, app **giữ cửa sổ
  mở và tự chờ** (mặc định tối đa `CAPTCHA_WAIT_SECONDS=180`); bạn chỉ cần giải
  captcha trong cửa sổ đó, app sẽ tự động lấy kết quả và tiếp tục.
- App đọc kết quả theo 2 lớp: bắt trực tiếp JSON `search/general/full`, và nếu
  không bắt được thì **đọc video đã render trong DOM** — nên chỉ cần trang tìm
  kiếm hiển thị video là lấy được kết quả.
- App **dùng lại một tab duy nhất** cho mọi lần tìm (không mở/đóng tab mới) và
  tự đóng tab trống mặc định của Chrome, nên cửa sổ luôn gọn gàng.
- Xong việc, cửa sổ **tự đóng** sau `BROWSER_IDLE_CLOSE_SECONDS` giây (mặc định
  `5`) nếu không có tìm kiếm mới. Đặt `0` để giữ mở.
- Cookie được lưu tại `USER_DATA_DIR` (`.browser-profile`) nên thường chỉ cần
  giải captcha **một lần**.
- Nếu captcha không được giải trong thời gian chờ, app **dừng cả lượt tìm** thay
  vì treo từng ngôn ngữ; các nhóm chưa chạy sẽ được báo là "bỏ qua".
- Nếu bạn tự đóng cửa sổ trình duyệt, app sẽ tự **mở lại** ở nhóm kế tiếp.
- Nếu máy chủ/IP bị TikTok gắn cờ và không hiện captcha giải được, tìm kiếm có
  thể trả về rỗng. Đổi IP/mạng hoặc đăng nhập TikTok trong cửa sổ trình duyệt sẽ
  ổn định hơn.
