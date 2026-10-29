"""Thin wrapper around Nebius Token Factory's OpenAI-compatible API."""
from __future__ import annotations

import json
import re
from typing import Optional, Sequence

import numpy as np
from openai import OpenAI

from .config import Settings

_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_reasoning(text: str) -> str:
    """Nemotron reasoning models may emit <think>…</think>; drop it from user-visible output."""
    text = _THINK.sub("", text or "")
    if "</think>" in text:  # opening tag was consumed server-side
        text = text.split("</think>", 1)[1]
    return text.strip()


def extract_json(text: str) -> dict:
    """Pull the first balanced JSON object out of a model reply (tolerates fences / chatter)."""
    text = strip_reasoning(text)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    if start != -1:  # only the first (outermost) object: an inner fragment of a truncated reply is not an answer
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except Exception:
                        break
    raise ValueError("Model did not return valid JSON")


class NebiusLLM:
    """Chat + embeddings against Nebius Token Factory using NVIDIA Nemotron models."""

    def __init__(self, s: Settings):
        self.s = s
        self._clients: dict[str, OpenAI] = {}
        self.calls = 0
        self.usage = {"prompt": 0, "completion": 0}
        self.last_finish: Optional[str] = None

    def _client(self, base_url: str) -> OpenAI:
        if base_url not in self._clients:
            self._clients[base_url] = OpenAI(base_url=base_url, api_key=self.s.api_key, timeout=120, max_retries=2)
        return self._clients[base_url]

    def _route(self, tier: str) -> tuple[str, str]:
        if tier == "fast":
            return self.s.fast_model, self.s.fast_base_url
        if tier == "deep":
            return self.s.deep_model, self.s.base_url
        return self.s.model, self.s.base_url

    def chat(self, messages: Sequence[dict], tier: str = "main", temperature: float = 0.2, max_tokens: int = 2048) -> str:
        model, base = self._route(tier)
        r = self._client(base).chat.completions.create(
            model=model, messages=list(messages), temperature=temperature, max_tokens=max_tokens
        )
        self.calls += 1
        self.last_finish = r.choices[0].finish_reason
        if getattr(r, "usage", None):
            self.usage["prompt"] += r.usage.prompt_tokens or 0
            self.usage["completion"] += r.usage.completion_tokens or 0
        return strip_reasoning(r.choices[0].message.content or "")

    def chat_json(self, messages: Sequence[dict], tier: str = "main", max_tokens: int = 12000) -> dict:
        msgs = list(messages)
        out = self.chat(msgs, tier=tier, temperature=0.1, max_tokens=max_tokens)
        try:
            return extract_json(out)
        except ValueError:
            msgs += [
                {"role": "assistant", "content": out[:4000]},
                {"role": "user", "content": "That was not valid JSON. Reply again with ONLY the JSON object, nothing else."},
            ]
            return extract_json(self.chat(msgs, tier=tier, temperature=0.0, max_tokens=int(max_tokens * 1.5)))

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        c = self._client(self.s.embed_base_url)
        out: list[list[float]] = []
        for i in range(0, len(texts), 48):
            r = c.embeddings.create(model=self.s.embed_model, input=list(texts[i : i + 48]))
            out += [d.embedding for d in r.data]
        self.calls += 1
        return np.asarray(out, dtype=np.float32)
