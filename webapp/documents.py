"""Uploaded documents (PDF, Word, text): text extraction and the legal references they cite.

Extraction is local (pypdf, python-docx). A scanned PDF without a text layer yields no text: the
app says so instead of guessing (no OCR, which would misread figures).
"""
from __future__ import annotations

import io
import re

MAX_BYTES = 20 * 1024 * 1024

ART = re.compile(r"(?:(?:[وبف]?(?:ال|لل))(?:مادة|مادتين|مواد|فصل|فصلين|فصول)|article|articles|art\.)\s+(\d{1,4}(?:\s*-\s*\d{1,3})?(?:\s*(?:مكرر|bis|ter))?)", re.I)
LAW = re.compile(r"(?:القانون|قانون|الظهير|ظهير|المرسوم|مرسوم|loi|dahir|décret)\s+(?:التنظيمي\s+)?(?:رقم|n°)?\s*(\d{1,3}[.\-]\d{2,4}(?:[.\-]\d{1,4})?)", re.I)
CODES = {"مدونة الشغل": "mudawwanat-shughl", "code du travail": "mudawwanat-shughl", "مدونة الأسرة": "mudawwanat-usra",
         "code de la famille": "mudawwanat-usra", "قانون الالتزامات والعقود": "doc", "code des obligations": "doc",
         "مدونة التجارة": "mudawwanat-tijara", "code de commerce": "mudawwanat-tijara",
         "القانون الجنائي": "qanun-jinai", "code pénal": "qanun-jinai", "المسطرة المدنية": "msm-58-25",
         "procédure civile": "msm-58-25", "المسطرة الجنائية": "msj", "procédure pénale": "msj",
         "مدونة الحقوق العينية": "huquq-ayniya-39-08", "التحفيظ العقاري": "tahfid-aqari"}


def extract(name: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ValueError("file larger than 20 MB")
    low = name.lower()
    if low.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    if low.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts).strip()
    if low.endswith((".txt", ".md")):
        return data.decode("utf-8", "replace").strip()
    raise ValueError("unsupported file type (PDF, DOCX, TXT)")


def references(text: str) -> dict:
    """Laws, codes and articles cited in a document: a starting point for the analysis."""
    low = text.lower()
    return {"laws": sorted({m.replace("-", ".") for m in LAW.findall(text)})[:50],
            "codes": sorted({slug for k, slug in CODES.items() if k in low}),
            "articles": sorted({re.sub(r"\s+", " ", a) for a in ART.findall(text)},
                               key=lambda x: [int(p) if p.isdigit() else 0 for p in re.findall(r"\d+", x)])[:200]}
