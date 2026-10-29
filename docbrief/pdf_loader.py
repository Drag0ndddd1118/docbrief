"""PDF -> page texts."""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader


@dataclass
class Document:
    name: str
    pages: list[str]  # index 0 == page 1
    sha: str = ""
    meta_title: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def n_pages(self) -> int:
        return len(self.pages)

    @property
    def n_chars(self) -> int:
        return sum(len(p) for p in self.pages)

    @property
    def full_text(self) -> str:
        return "\n".join(self.pages)

    def marked_text(self) -> str:
        """Text with [[Page N]] markers so the LLM can cite page numbers."""
        return "\n\n".join(f"[[Page {i}]]\n{t}" for i, t in enumerate(self.pages, 1))


def clean_text(t: str) -> str:
    t = t.replace("\x00", " ").replace("\u00a0", " ")
    t = re.sub(r"-\n(?=[a-z])", "", t)  # de-hyphenate line wraps
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def load_pdf(data: bytes, name: str = "document.pdf") -> Document:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("This PDF is password-protected.")
    pages, warnings = [], []
    for i, page in enumerate(reader.pages, 1):
        try:
            pages.append(clean_text(page.extract_text() or ""))
        except Exception as e:  # pragma: no cover - defensive
            pages.append("")
            warnings.append(f"Page {i}: text extraction failed ({e}).")
    if not any(pages):
        raise ValueError(
            "No extractable text found. This looks like a scanned PDF — run OCR first (e.g. ocrmypdf)."
        )
    empty = sum(1 for p in pages if len(p) < 20)
    if empty:
        warnings.append(f"{empty} page(s) had little or no extractable text (scans/images are skipped).")
    title = ""
    try:
        title = (reader.metadata.title or "").strip() if reader.metadata else ""
    except Exception:
        pass
    return Document(name=name, pages=pages, sha=hashlib.sha1(data).hexdigest()[:12], meta_title=title, warnings=warnings)
