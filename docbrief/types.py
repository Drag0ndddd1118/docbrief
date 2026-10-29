from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Point:
    text: str
    page: Optional[int] = None


@dataclass
class Metric:
    name: str
    value: str
    period: str = ""
    page: Optional[int] = None
    note: str = ""
    verified: Optional[bool] = None  # value literally found in the PDF text?


@dataclass
class Analysis:
    title: str = ""
    doc_type: str = "other"  # financial_report | research_paper | other
    tldr: str = ""
    summary: str = ""
    key_points: list[Point] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    risks: list[Point] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    engine: str = ""  # description of what produced this (models / offline)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Source:
    label: str  # "S1" / "W1"
    page: Optional[int]
    text: str
    url: str = ""


@dataclass
class Answer:
    text: str
    sources: list[Source] = field(default_factory=list)
    engine: str = ""
