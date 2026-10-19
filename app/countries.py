"""Ánh xạ quốc gia <-> ngôn ngữ.

- ``TRENDING_COUNTRIES``: các quốc gia hiện được TikTok Creative Center hỗ
  trợ cho bảng xếp hạng video (Top Contents).
- ``COUNTRIES``: danh sách rộng hơn dùng cho tìm kiếm từ khóa.
"""
from __future__ import annotations

# Quốc gia có bảng xếp hạng "trending" trên Creative Center.
TRENDING_COUNTRIES: dict[str, str] = {
    "VN": "Vietnam",
    "US": "United States",
    "JP": "Japan",
    "TH": "Thailand",
    "ID": "Indonesia",
}

# Mã ngôn ngữ ISO-639-1 phổ biến cho mỗi quốc gia (dùng để tự dịch từ khóa).
COUNTRIES: dict[str, dict] = {
    "VN": {"name": "Vietnam", "languages": ["vi"]},
    "US": {"name": "United States", "languages": ["en"]},
    "GB": {"name": "United Kingdom", "languages": ["en"]},
    "AU": {"name": "Australia", "languages": ["en"]},
    "CA": {"name": "Canada", "languages": ["en", "fr"]},
    "JP": {"name": "Japan", "languages": ["ja"]},
    "KR": {"name": "South Korea", "languages": ["ko"]},
    "TH": {"name": "Thailand", "languages": ["th"]},
    "ID": {"name": "Indonesia", "languages": ["id"]},
    "PH": {"name": "Philippines", "languages": ["en", "tl"]},
    "MY": {"name": "Malaysia", "languages": ["ms", "en"]},
    "SG": {"name": "Singapore", "languages": ["en", "zh"]},
    "IN": {"name": "India", "languages": ["en", "hi"]},
    "BR": {"name": "Brazil", "languages": ["pt"]},
    "MX": {"name": "Mexico", "languages": ["es"]},
    "ES": {"name": "Spain", "languages": ["es"]},
    "FR": {"name": "France", "languages": ["fr"]},
    "DE": {"name": "Germany", "languages": ["de"]},
    "IT": {"name": "Italy", "languages": ["it"]},
    "NL": {"name": "Netherlands", "languages": ["nl"]},
    "TR": {"name": "Türkiye", "languages": ["tr"]},
    "SA": {"name": "Saudi Arabia", "languages": ["ar"]},
    "AE": {"name": "United Arab Emirates", "languages": ["ar", "en"]},
    "RU": {"name": "Russia", "languages": ["ru"]},
    "CN": {"name": "China", "languages": ["zh"]},
    "TW": {"name": "Taiwan", "languages": ["zh"]},
}

LANGUAGE_NAMES: dict[str, str] = {
    "vi": "Tiếng Việt",
    "en": "English",
    "th": "ไทย (Thai)",
    "ja": "日本語 (Japanese)",
    "ko": "한국어 (Korean)",
    "id": "Bahasa Indonesia",
    "tl": "Filipino",
    "ms": "Bahasa Melayu",
    "zh": "中文 (Chinese)",
    "hi": "हिन्दी (Hindi)",
    "pt": "Português",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "nl": "Nederlands",
    "tr": "Türkçe",
    "ar": "العربية (Arabic)",
    "ru": "Русский",
}


def languages_for_countries(codes: list[str]) -> list[str]:
    """Gộp danh sách ngôn ngữ của nhiều quốc gia, giữ thứ tự, không trùng."""
    out: list[str] = []
    for code in codes:
        for lang in COUNTRIES.get(code.upper(), {}).get("languages", []):
            if lang not in out:
                out.append(lang)
    return out
