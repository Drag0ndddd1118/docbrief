from __future__ import annotations

from .config import Settings
from .live import LiveEngine
from .mock import MockEngine


def get_engine(s: Settings | None = None):
    s = s or Settings.from_env()
    return LiveEngine(s) if s.is_live else MockEngine()
