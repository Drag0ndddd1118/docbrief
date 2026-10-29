"""Document-type detection, metric grounding checks, and regex metric extraction (offline fallback)."""
from __future__ import annotations

import re
from collections import Counter

from .types import Metric

FIN_WORDS = [
    "revenue", "net income", "operating income", "gross margin", "gross profit", "ebitda", "earnings per share",
    "eps", "balance sheet", "cash flow", "fiscal", "dividend", "guidance", "shareholders", "10-k", "annual report",
    "quarter", "backlog", "operating expenses",
]
PAPER_WORDS = [
    "abstract", "introduction", "related work", "methodology", "we propose", "experiments", "references",
    "dataset", "baseline", "ablation", "arxiv", "et al", "hypothesis", "limitations", "conclusion",
]


def detect_doc_type(text: str) -> str:
    low = text.lower()
    fin = sum(low.count(w) for w in FIN_WORDS)
    pap = sum(low.count(w) for w in PAPER_WORDS)
    if fin >= 12 and fin >= pap:
        return "financial_report"
    if pap >= 6:
        return "research_paper"
    return "financial_report" if fin > pap else "other"


def _norm(s: str) -> str:
    return re.sub(r"[\s,$¥€£]", "", s.lower())


def verify_metrics(metrics: list[Metric], full_text: str) -> list[Metric]:
    """Mark each metric as verified only if its numeric value literally appears in the PDF text."""
    hay = _norm(full_text)
    for m in metrics:
        nums = re.findall(r"\d[\d,]*\.?\d*", m.value)
        m.verified = bool(nums) and all(_norm(n) in hay for n in nums[:2])
    return metrics


# (display name, label regex)
_LABELS = [
    ("Revenue", r"(?:total |net )?revenues?"),
    ("Gross margin", r"gross (?:profit )?margin"),
    ("Operating income", r"operating income"),
    ("Operating margin", r"operating margin"),
    ("Net income", r"net income"),
    ("Diluted EPS", r"diluted (?:earnings per share|eps)|diluted eps"),
    ("R&D expense", r"(?:r&d|research and development)(?: expense| spending| investment)?"),
    ("Operating cash flow", r"(?:cash (?:flow )?(?:generated )?(?:from|provided by) operat\w+|operating cash flow)"),
    ("Free cash flow", r"free cash flow"),
    ("Cash & equivalents", r"cash and cash equivalents"),
    ("Total debt", r"total debt"),
    ("Backlog", r"(?:order )?backlog"),
    ("FY guidance (revenue)", r"(?:revenue )?guidance|outlook"),
]
_VAL = re.compile(r"(?:US)?\$?\s?\d[\d,]*\.?\d*\s?(?:%|million|billion|bn|m\b|M\b|B\b)?(?:\s?(?:to|[-–])\s?\$?\d[\d,]*\.?\d*\s?(?:million|billion|%)?)?")


def _sentences(pages: list[str]):
    for pno, t in enumerate(pages, 1):
        for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s*\n\s*", " ", t)):
            s = s.strip()
            if len(s) > 15:
                yield pno, s


def _period(sentence: str, default: str) -> str:
    m = re.search(r"(?:fiscal(?: year)?|FY)\s?'?(20\d\d)", sentence, re.I)
    return f"FY{m.group(1)}" if m else default


def regex_metrics(pages: list[str]) -> list[Metric]:
    text = "\n".join(pages)
    years = Counter(re.findall(r"(?:fiscal(?: year)?|FY)\s?'?(20\d\d)", text, re.I))
    default = f"FY{years.most_common(1)[0][0]}" if years else ""
    out: list[Metric] = []
    seen: set[str] = set()
    sents = list(_sentences(pages))
    for name, label in _LABELS:
        for pno, s in sents:
            m = re.search(label, s, re.I)
            if not m:
                continue
            tail = s[m.end() :]
            want_pct = "margin" in name.lower()
            v = None
            if want_pct:  # "12.7% operating margin" — number precedes the label
                pre = re.search(r"(\d[\d.]*\s?%)\s*(?:\w+\s)?$", s[: m.start()])
                if pre:
                    v = pre.group(1)
            cands = [c.group(0).strip() for c in _VAL.finditer(tail)]
            if v is None:
                pref = (lambda r: "%" in r) if want_pct else (lambda r: bool(re.search(r"[$]|million|billion|bn", r, re.I)))
                for raw in cands:
                    if pref(raw):
                        v = raw
                        break
                if v is None and name == "Diluted EPS":
                    v = next((c for c in cands if re.search(r"\d\.\d\d", c)), None)
            if v and "guidance" not in name.lower() and re.match(r"^\d[\d.]*\s?%\s?(?:to|[-–])\s?\$", v):
                v = re.split(r"(?:to|[-–])\s?", v, maxsplit=1)[1]
            if v and name not in seen:
                seen.add(name)
                per = _period(s, default) if "guidance" in name.lower() else default
                out.append(Metric(name=name, value=v.strip(" ,."), period=per, page=pno, note=s[:160]))
                break
    return out
