"""Deterministic, low-risk final response hygiene and offline quality heuristics.

Never use an LLM to rewrite transaction confirmations or developer errors.
"""
from __future__ import annotations
import re

def concise_public_reply(message: str) -> str:
    text = re.sub(r'[\t ]+', ' ', message.strip())
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Don't strip useful meaning; simply remove repetitive openings where they are exact duplicates.
    text = re.sub(r'^(Hello(?: there)?[!.]\s*){2,}', 'Hello. ', text, flags=re.I)
    return text[:3000]

def quality_signals(reply: str) -> dict[str, bool | int]:
    """Deterministic signals for review, not a claim of model quality or factuality."""
    s = reply.strip()
    return {
        'not_empty': bool(s),
        'reasonable_length': 0 < len(s) <= 3000,
        'no_internal_brand': not bool(re.search(r'\bjoomla\b', s, re.I)),
        'no_unverified_confirmation': not bool(re.search(r'(?i)^(?:i (?:have )?(?:charged|sent the money)|payment (?:has been )?completed)\b',s)),
        'has_question': '?' in s,
        'word_count': len(s.split()),
    }
