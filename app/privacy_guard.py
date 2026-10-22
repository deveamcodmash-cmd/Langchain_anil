"""Block likely credentials or payment-card numbers before any model call.

This is a defense-in-depth pattern check, not a substitute for UI data loss
prevention or platform-side redaction. It never logs or returns the secret.
"""
from __future__ import annotations
import re

SECRET = re.compile(
    r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|whsec_[A-Za-z0-9_]{16,}|'
    r'(?:api[_ -]?key|password|client[_ -]?secret)\s*[:=]\s*\S{8,})',
    re.IGNORECASE,
)
POSSIBLE_CARD = re.compile(r'(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)')


def _luhn_valid(number: str) -> bool:
    if not 13 <= len(number) <= 19:
        return False
    digits=[int(c) for c in number]
    check=0
    for position,digit in enumerate(reversed(digits)):
        if position % 2:
            digit *= 2
            if digit > 9: digit -= 9
        check += digit
    return check % 10 == 0


def contains_sensitive_payment_data(message: str) -> bool:
    if SECRET.search(message): return True
    return any(_luhn_valid(re.sub(r'\D','',match.group())) for match in POSSIBLE_CARD.finditer(message))
