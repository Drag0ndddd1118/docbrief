"""Abuse protection for a public, key-sharing demo.

Three layers, all configurable through environment variables / Streamlit secrets:

1. **Per-session quotas**   – analyses, questions, deep questions, fact-checks.
2. **Input limits**         – PDF size, page count, analysed characters, question length.
3. **Global daily budget**  – a small file-backed counter (resets at 00:00 UTC) that every live call spends from.
   When it is empty the app keeps working on pre-computed results only.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import MutableMapping

from .config import _secret


def _int(name: str, default: int) -> int:
    try:
        return int(_secret(name) or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Limits:
    max_analyses: int = 3  # per browser session
    max_questions: int = 10
    max_deep_questions: int = 2  # Nemotron Ultra is the expensive tier
    max_factchecks: int = 2
    max_pdf_mb: int = 15
    max_pages: int = 80
    max_analysis_chars: int = 150_000  # ≈ 4 map sections; later pages are still searchable in Q&A
    max_chunks: int = 450  # embedding cap
    max_question_chars: int = 600
    daily_budget: int = 400  # "units" per UTC day, shared by all visitors

    @classmethod
    def from_env(cls, get=None) -> "Limits":
        d = cls()
        return cls(
            max_analyses=_int("DOCBRIEF_MAX_ANALYSES", d.max_analyses),
            max_questions=_int("DOCBRIEF_MAX_QUESTIONS", d.max_questions),
            max_deep_questions=_int("DOCBRIEF_MAX_DEEP", d.max_deep_questions),
            max_factchecks=_int("DOCBRIEF_MAX_FACTCHECKS", d.max_factchecks),
            max_pdf_mb=_int("DOCBRIEF_MAX_PDF_MB", d.max_pdf_mb),
            max_pages=_int("DOCBRIEF_MAX_PAGES", d.max_pages),
            max_analysis_chars=_int("DOCBRIEF_MAX_ANALYSIS_CHARS", d.max_analysis_chars),
            max_chunks=_int("DOCBRIEF_MAX_CHUNKS", d.max_chunks),
            max_question_chars=_int("DOCBRIEF_MAX_QUESTION_CHARS", d.max_question_chars),
            daily_budget=_int("DOCBRIEF_DAILY_BUDGET", d.daily_budget),
        )


# cost of one action in daily-budget units (roughly proportional to model tokens)
COST = {"analysis": 12, "question": 2, "deep": 8, "factcheck": 8}


class DailyLedger:
    """Process-wide, thread-safe daily counter persisted to a small JSON file."""

    def __init__(self, budget: int, path: str | os.PathLike | None = None):
        self.budget = budget
        self.path = Path(path) if path else Path(tempfile.gettempdir()) / "docbrief_usage.json"
        self._lock = threading.Lock()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _read(self) -> dict:
        try:
            d = json.loads(self.path.read_text())
            if d.get("date") == self._today():
                return d
        except Exception:
            pass
        return {"date": self._today(), "used": 0, "by_kind": {}}

    def _write(self, d: dict) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(d))
            tmp.replace(self.path)
        except Exception:  # an unwritable temp dir must not break the app; the in-memory fallback below still applies
            pass

    def used(self) -> int:
        with self._lock:
            return self._read()["used"]

    def remaining(self) -> int:
        return max(0, self.budget - self.used())

    def try_spend(self, kind: str) -> bool:
        """Atomically spend the cost of `kind`; False (and no spend) if the daily budget would be exceeded."""
        cost = COST[kind]
        with self._lock:
            d = self._read()
            if d["used"] + cost > self.budget:
                return False
            d["used"] += cost
            d["by_kind"][kind] = d["by_kind"].get(kind, 0) + 1
            self._write(d)
            return True


class SessionQuota:
    """Per-session counters stored in any mutable mapping (st.session_state in the app)."""

    KINDS = {"analysis": "max_analyses", "question": "max_questions", "deep": "max_deep_questions", "factcheck": "max_factchecks"}

    def __init__(self, store: MutableMapping, limits: Limits, ledger: DailyLedger):
        self.store, self.limits, self.ledger = store, limits, ledger

    def _key(self, kind: str) -> str:
        return f"_quota_{kind}"

    def used(self, kind: str) -> int:
        return int(self.store.get(self._key(kind), 0))

    def cap(self, kind: str) -> int:
        return getattr(self.limits, self.KINDS[kind])

    def left(self, kind: str) -> int:
        return max(0, self.cap(kind) - self.used(kind))

    def check(self, kind: str) -> str | None:
        """Return a user-facing reason if `kind` is not allowed right now, else None (nothing is spent)."""
        if self.left(kind) <= 0:
            return f"Session limit reached ({self.cap(kind)} {kind.replace('factcheck', 'fact-check')}s per session). Everything pre-computed stays available."
        if self.ledger.remaining() < COST[kind]:
            return "Today's shared demo budget is used up, so live calls are paused until 00:00 UTC. The pre-computed NVIDIA 10-K demo still works."
        return None

    def spend(self, kind: str) -> str | None:
        """Check, then spend from both the session quota and the global ledger. Returns a reason on refusal."""
        why = self.check(kind)
        if why:
            return why
        if not self.ledger.try_spend(kind):
            return "Today's shared demo budget is used up, so live calls are paused until 00:00 UTC. The pre-computed NVIDIA 10-K demo still works."
        self.store[self._key(kind)] = self.used(kind) + 1
        return None


def validate_upload(size_bytes: int, n_pages: int | None, limits: Limits) -> str | None:
    if size_bytes > limits.max_pdf_mb * 1024 * 1024:
        return f"This PDF is {size_bytes / 1024 / 1024:.1f} MB; the public demo accepts up to {limits.max_pdf_mb} MB."
    if n_pages is not None and n_pages > limits.max_pages:
        return f"This PDF has {n_pages} pages; the public demo accepts up to {limits.max_pages}. Upload an excerpt (e.g. just the MD&A)."
    return None
