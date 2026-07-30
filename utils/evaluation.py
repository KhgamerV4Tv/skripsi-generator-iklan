"""Helpers for interpreting the LLM-as-a-Judge result."""

from __future__ import annotations

import re


def parse_quality_score(evaluation_text: str) -> int | None:
    """Extract and validate the quality score from the agreed output format."""
    match = re.search(r"SKOR KELAYAKAN:\s*(\d{1,3})", evaluation_text or "", re.IGNORECASE)
    if not match:
        return None
    score = int(match.group(1))
    return score if 0 <= score <= 100 else None


def classify_quality_score(score: int) -> dict[str, str]:
    """Map the thesis evaluation thresholds to a UI-friendly result."""
    if not 0 <= score <= 100:
        raise ValueError("Skor harus berada di antara 0 dan 100.")
    if score >= 85:
        return {
            "code": "pass",
            "label": "Lulus Uji Kualitas Pakar AI",
            "summary": "Naskah memenuhi standar kelayakan tanpa revisi material.",
        }
    if score >= 70:
        return {
            "code": "minor",
            "label": "Lulus Bersyarat — Revisi Minor",
            "summary": "Naskah layak digunakan setelah perbaikan kecil pada temuan evaluasi.",
        }
    return {
        "code": "revise",
        "label": "Perlu Revisi",
        "summary": "Naskah belum memenuhi batas kelayakan dan perlu dievaluasi ulang.",
    }
