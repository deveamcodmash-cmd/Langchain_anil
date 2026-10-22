"""Explicit opt-in preference transport. Storage and identity belong to Joomla.

Preferences may affect style and topics, never authorize actions or establish
payment, booking, donation or identity facts. Never write server-side user memory
on the stateless model service.
"""
from __future__ import annotations
import re

_BLOCKED = re.compile(
    r"(?:ignore (?:all|previous|the) instructions|system prompt|developer message|"
    r"(?:api|access|secret)\s*key|password|cvv|card\s*number|private\s*key|"
    r"bearer\s+token|sk-(?:proj-)?[a-z0-9_-]{8,}|"
    r"\b(?:my|i have|i am)\s+(?:diagnosed|diabetic|hiv|pregnant)\b)",re.I
)

def safe_preferences(items: list[str]) -> list[str]:
    out: list[str] = []
    for raw in items[:8]:
        text = ' '.join(str(raw).split())[:250]
        if not text or _BLOCKED.search(text):
            continue
        if text.casefold() not in {s.casefold() for s in out}:
            out.append(text)
    return out
