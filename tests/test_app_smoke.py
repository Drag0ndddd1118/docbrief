"""End-to-end smoke test of the Streamlit UI (offline mode, no network): landing -> preloaded 10-K -> cached answer."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_landing_then_showcase_and_cached_answer():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("Ask any 10-K" in m.value for m in at.markdown)
    next(b for b in at.button if "preloaded NVIDIA 10-K" in b.label).click()
    at.run()
    assert not at.exception
    assert any("TL;DR" in m.value for m in at.markdown)
    at.radio(key="view").set_value("💬 Ask the document").run()
    q = next(b for b in at.button if "customers" in b.label)
    q.click()
    at.run()
    assert not at.exception
    assert any("22" in m.value and "[p.7]" in m.value for m in at.chat_message[1].markdown)  # served from the pre-computed cache
