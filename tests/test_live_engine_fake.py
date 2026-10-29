"""Exercises the LIVE engine code path against a fake LLM (no network, no API key)."""
import json
from pathlib import Path

import numpy as np

from docbrief.chunking import chunk_document
from docbrief.config import Settings
from docbrief.live import LiveEngine
from docbrief.pdf_loader import load_pdf

REPORT = Path(__file__).resolve().parents[1] / "samples" / "aurora_robotics_fy2025_report.pdf"


class FakeLLM:
    calls = 0

    def __init__(self, *a, **k):
        self.log = []

    def chat_json(self, messages, tier="main", max_tokens=0):
        self.log.append(tier)
        return {
            "title": "Aurora FY2025", "doc_type": "financial_report", "tldr": "Growth.", "summary": "Strong year.",
            "key_points": [{"text": "Revenue grew", "page": 1}],
            "metrics": [{"name": "Revenue", "value": "$482.6 million", "period": "FY2025", "page": 1},
                        {"name": "Fake", "value": "$1,234.5 million", "period": "FY2025", "page": 1}],
            "risks": [{"text": "Customer concentration", "page": 4}], "suggested_questions": ["a", "b", "c"],
        }

    def chat(self, messages, tier="main", temperature=0.2, max_tokens=0):
        self.log.append(tier)
        return "Guidance is $560-$580 million [p.4]."

    def embed(self, texts):
        rng = np.random.default_rng(0)
        return rng.normal(size=(len(texts), 16)).astype("float32")


def test_live_path(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "fake")
    s = Settings.from_env()
    eng = LiveEngine(s)
    eng.llm = FakeLLM()
    doc = load_pdf(REPORT.read_bytes(), REPORT.name)
    a = eng.analyze(doc)
    assert a.metrics[0].verified is True and a.metrics[1].verified is False  # grounding check catches the fake number
    r = eng.build_retriever(chunk_document(doc))
    assert r.mode.startswith("hybrid")
    ans = eng.answer(doc, r, "2026年的收入指引是多少？", deep=True)
    assert "[p.4]" in ans.text and "fast" in eng.llm.log and "deep" in eng.llm.log  # query rewrite (fast) + deep answer


def test_analyze_cost_cap_truncates_long_documents(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "fake")
    eng = LiveEngine(Settings.from_env())
    eng.llm = FakeLLM()
    doc = load_pdf(REPORT.read_bytes(), REPORT.name)
    eng.analyze(doc, max_chars=1500)
    assert any("cost cap" in w for w in doc.warnings)
    doc2 = load_pdf(REPORT.read_bytes(), REPORT.name)
    eng.analyze(doc2)
    assert not any("cost cap" in w for w in doc2.warnings)
