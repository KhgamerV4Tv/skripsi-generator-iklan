"""Optional reverse-image-search integration for visual risk review."""

from __future__ import annotations

import base64
from typing import Any
from urllib.parse import urlparse


class CopyrightCheckError(RuntimeError):
    """A user-safe failure raised by the optional similarity check."""


def classify_visual_matches(match_count: int) -> dict[str, str]:
    """Classify provider matches without inventing a similarity percentage."""
    if match_count < 0:
        raise ValueError("Jumlah padanan tidak boleh negatif.")
    if match_count == 0:
        return {
            "code": "low",
            "label": "Tidak ada padanan terdeteksi",
            "summary": "Tidak ditemukan padanan pada hasil pencarian saat ini.",
        }
    if match_count < 5:
        return {
            "code": "review",
            "label": "Perlu tinjauan manual",
            "summary": "Ada beberapa padanan visual; periksa sumber sebelum publikasi.",
        }
    return {
        "code": "high",
        "label": "Risiko kemiripan lebih tinggi",
        "summary": "Banyak padanan visual ditemukan; pertimbangkan render atau revisi ulang.",
    }


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalise_match(match: dict[str, Any]) -> dict[str, str]:
    title = str(match.get("title") or match.get("source") or "Sumber visual").strip()
    link = str(match.get("link") or "").strip()
    source = str(match.get("source") or "").strip()
    return {
        "title": title[:160],
        "source": source[:100],
        "link": link if _is_http_url(link) else "",
    }


def upload_to_imgbb(image_bytes: bytes, api_key: str, *, timeout: int = 20) -> str:
    """Upload a generated image temporarily so Google Lens can access it."""
    import requests

    if not image_bytes:
        raise CopyrightCheckError("Gambar belum tersedia untuk diperiksa.")
    if not api_key:
        raise CopyrightCheckError("IMGBB_API_KEY belum dikonfigurasi.")

    try:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": api_key},
            data={"image": base64.b64encode(image_bytes).decode("ascii")},
            timeout=timeout,
        )
        response.raise_for_status()
        public_url = str(response.json().get("data", {}).get("url") or "")
    except (requests.RequestException, ValueError) as exc:
        raise CopyrightCheckError("Layanan unggah gambar sementara gagal merespons.") from exc

    if not _is_http_url(public_url):
        raise CopyrightCheckError("Layanan unggah tidak mengembalikan URL gambar yang valid.")
    return public_url


def run_google_lens_check(
    image_bytes: bytes,
    *,
    imgbb_api_key: str,
    serpapi_api_key: str,
    max_matches: int = 4,
) -> dict[str, Any]:
    """Return match counts and sources; this is not a legal copyright verdict."""
    if not serpapi_api_key:
        raise CopyrightCheckError("SERPAPI_API_KEY belum dikonfigurasi.")

    public_url = upload_to_imgbb(image_bytes, imgbb_api_key)
    try:
        from serpapi import GoogleSearch

        result = GoogleSearch(
            {
                "engine": "google_lens",
                "url": public_url,
                "api_key": serpapi_api_key,
            }
        ).get_dict()
    except Exception as exc:
        raise CopyrightCheckError("Google Lens/SerpAPI gagal memproses pemeriksaan.") from exc

    if result.get("error"):
        raise CopyrightCheckError("Google Lens/SerpAPI menolak permintaan pemeriksaan.")

    raw_matches = result.get("visual_matches") or []
    match_count = len(raw_matches)
    return {
        "match_count": match_count,
        "risk": classify_visual_matches(match_count),
        "matches": [_normalise_match(item) for item in raw_matches[:max_matches]],
        "disclaimer": (
            "Hasil reverse image search hanya sinyal kemiripan, bukan penetapan "
            "orisinalitas atau nasihat hukum."
        ),
    }
