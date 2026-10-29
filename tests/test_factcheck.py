"""Web fact-check path with a fake LLM and a fake Tavily client (no network, no keys)."""
from pathlib import Path

from docbrief.config import Settings
from docbrief.live import LiveEngine
from docbrief.pdf_loader import load_pdf
from docbrief.tavily import tavily_search
from docbrief.types import Analysis, Source

REPORT = Path(__file__).resolve().parents[1] / "samples" / "aurora_robotics_fy2025_report.pdf"


class FakeLLM:
    def __init__(self):
        self.tiers = []

    def chat_json(self, messages, tier="main", max_tokens=0):
        self.tiers.append(tier)
        if "planner" in messages[0]["content"]:
            return {"claims": [
                {"claim": "market growing at only about 6% per year", "page": 2, "query": "warehouse automation market CAGR 2030"},
                {"claim": "e-commerce is about 20% of retail", "page": 2, "query": "ecommerce share of global retail sales"},
                {"claim": "", "page": 1, "query": "dropped: empty claim"},
            ]}
        assert "[W1]" in messages[1]["content"] and "[W2]" in messages[1]["content"]  # web snippets reach the judge
        return {"results": [
            {"index": 0, "verdict": "differs", "pdf_says": "6% [p.2]", "web_says": "10-15% CAGR [W1]", "explanation": "Lower than the web range."},
            {"index": 1, "verdict": "bogus-verdict", "pdf_says": "20% [p.2]", "web_says": "20.1% [W2]", "explanation": "Matches."},
        ]}


def _engine(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "fake")
    eng = LiveEngine(Settings.from_env())
    eng.llm = FakeLLM()
    return eng


def test_fact_check_reconciles_pdf_vs_web(monkeypatch):
    eng = _engine(monkeypatch)
    doc = load_pdf(REPORT.read_bytes(), REPORT.name)
    queries = []

    def fake_tavily(q, start=1):
        queries.append(q)
        return [Source(label=f"W{start}", page=None, text="CAGR of 14.58% to 2030", url=f"https://example.com/{start}", title="Report")]

    out = eng.fact_check(doc, Analysis(title="Aurora"), fake_tavily)
    assert len(out) == 2 and queries == ["warehouse automation market CAGR 2030", "ecommerce share of global retail sales"]
    assert out[0].verdict == "differs" and out[0].sources[0].label == "W1" and out[1].sources[0].label == "W2"  # globally unique labels
    assert out[1].verdict == "no_web_evidence"  # unknown verdicts are normalised, never trusted blindly
    assert eng.llm.tiers == ["fast", "main"]  # Nano plans, Super judges


def test_fact_check_survives_search_failure(monkeypatch):
    eng = _engine(monkeypatch)
    doc = load_pdf(REPORT.read_bytes(), REPORT.name)

    def boom(q, start=1):
        raise RuntimeError("tavily down")

    out = eng.fact_check(doc, Analysis(title="x"), boom)
    assert out and all(c.sources == [] for c in out)


def test_tavily_client_parses_and_dedupes(monkeypatch):
    class R:
        def raise_for_status(self): pass
        def json(self):
            return {"results": [
                {"url": "https://a.com/x?utm=1", "title": "A", "content": "one"},
                {"url": "https://a.com/x?utm=2", "title": "A dup", "content": "dup"},
                {"url": "https://b.com/y", "title": "B", "content": "two"},
            ]}

    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, auth=headers["Authorization"], body=json)
        return R()

    monkeypatch.setattr("docbrief.tavily.requests.post", fake_post)
    src = tavily_search("q", "tvly-test", max_results=3, start_label=4)
    assert [s.label for s in src] == ["W4", "W5"] and src[0].url == "https://a.com/x" and src[1].title == "B"
    assert sent["url"].endswith("/search") and sent["auth"] == "Bearer tvly-test"
