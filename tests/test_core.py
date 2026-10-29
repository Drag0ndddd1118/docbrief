from pathlib import Path

import pytest

from docbrief.chunking import chunk_document
from docbrief.config import Settings
from docbrief.engine import get_engine
from docbrief.llm import extract_json, strip_reasoning
from docbrief.metrics import detect_doc_type, verify_metrics
from docbrief.pdf_loader import load_pdf
from docbrief.retrieval import Retriever, tokenize
from docbrief.types import Metric

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "samples" / "aurora_robotics_fy2025_report.pdf"
PAPER = ROOT / "samples" / "retrieval_augmented_earnings_forecasting_paper.pdf"


@pytest.fixture(scope="module")
def report():
    return load_pdf(REPORT.read_bytes(), REPORT.name)


def test_pdf_loads(report):
    assert report.n_pages == 4 and "482.6" in report.full_text


def test_doc_type(report):
    assert detect_doc_type(report.full_text) == "financial_report"
    assert detect_doc_type(load_pdf(PAPER.read_bytes()).full_text) == "research_paper"


def test_mock_mode_without_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.setenv("DOCBRIEF_MODE", "auto")
    s = Settings.from_env()
    assert s.mode == "mock"


def test_live_requires_key(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "x")
    monkeypatch.setenv("DOCBRIEF_MODE", "auto")
    assert Settings.from_env().mode == "live"


def test_mock_analysis_and_qa(report, monkeypatch):
    monkeypatch.setenv("DOCBRIEF_MODE", "mock")
    eng = get_engine()
    a = eng.analyze(report)
    names = {m.name: m for m in a.metrics}
    assert names["Revenue"].value == "$482.6 million" and names["Revenue"].verified
    assert names["Diluted EPS"].value == "$1.21"
    r = eng.build_retriever(chunk_document(report))
    ans = eng.answer(report, r, "What is the revenue guidance for fiscal 2026?")
    assert "$560 million" in ans.text and "[p.4]" in ans.text


def test_verify_flags_hallucinated_number(report):
    ms = verify_metrics([Metric("Revenue", "$999.9 million"), Metric("Net income", "$48.2 million")], report.full_text)
    assert ms[0].verified is False and ms[1].verified is True


def test_retrieval_bm25(report):
    r = Retriever(chunk_document(report))
    top = r.search("customer concentration ten largest customers")[0][0]
    assert top.page == 4


def test_chinese_tokenizer():
    assert "营收" in tokenize("公司营收增长")


def test_json_extraction():
    assert extract_json('<think>hmm {x}</think>\n```json\n{"a": {"b": 1}}\n```') == {"a": {"b": 1}}
    assert extract_json('Sure! here: {"a": "}"} thanks') == {"a": "}"}
    assert strip_reasoning("<think>x</think>hello") == "hello"


def test_extract_json_rejects_truncated_reply():
    import pytest
    from docbrief.llm import extract_json

    truncated = '{"title": "x", "key_points": [{"text": "a", "page": 1}, {"text": "b", "pa'
    with pytest.raises(ValueError):  # must not return the inner {"text": "a", "page": 1} fragment
        extract_json(truncated)
