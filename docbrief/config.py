"""Runtime configuration, read from environment variables (and an optional .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv() -> None:
    if os.environ.get("DOCBRIEF_NO_DOTENV"):  # used by the test-suite so a real .env never leaks into tests
        return
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # python-dotenv missing is fine
        pass


def _secret(key: str) -> str:
    """Environment first, then Streamlit secrets (Streamlit Community Cloud: App settings -> Secrets)."""
    v = os.environ.get(key)
    if v:
        return v
    if os.environ.get("DOCBRIEF_NO_DOTENV"):
        return ""
    try:
        import streamlit as st

        return str(st.secrets.get(key, "") or "")
    except Exception:  # no secrets file / not running under streamlit
        return ""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    fast_base_url: str
    embed_base_url: str
    model: str
    fast_model: str
    deep_model: str
    embed_model: str
    mode: str  # "live" or "mock"
    tavily_key: str

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        g = lambda k, d="": (_secret(k) or d).strip()  # noqa: E731
        api_key = g("NEBIUS_API_KEY")
        requested = g("DOCBRIEF_MODE", "auto").lower()
        if requested == "mock":
            mode = "mock"
        elif requested == "live":
            mode = "live" if api_key else "mock"  # live needs a key; degrade gracefully
        else:
            mode = "live" if api_key else "mock"
        return cls(
            api_key=api_key,
            base_url=g("NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/"),
            fast_base_url=g("NEBIUS_FAST_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
            embed_base_url=g("NEBIUS_EMBED_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
            model=g("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
            fast_model=g("NEBIUS_FAST_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"),
            deep_model=g("NEBIUS_DEEP_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b"),
            embed_model=g("NEBIUS_EMBED_MODEL", "Qwen/Qwen3-Embedding-8B"),
            mode=mode,
            tavily_key=g("TAVILY_API_KEY"),
        )
