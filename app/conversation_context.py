"""Bounded conversational continuity, not an authority or a model-controlled memory store.

All context derives from the existing account/browser conversation. Platform facts,
bookings, plan edits and payments must still be read from trusted application data.
"""
from __future__ import annotations
import re
from typing import Any

VAGUE_FOLLOWUP = re.compile(
    r"^(?:and\s+)?(?:what\s+about\s+(?:that|it|this)|how\s+does\s+(?:that|it|this)\s+work|"
    r"can\s+you\s+explain\s+(?:that|it)|tell\s+me\s+more\s+about\s+(?:that|it)|"
    r"is\s+(?:that|it)\s+(?:available|possible)|why\s+is\s+(?:that|it)\s+so)[?.! ]*$",
    re.IGNORECASE,
)


def focused_knowledge_query(message: str, history: list[dict[str, Any]]) -> str:
    """Use prior subject words to retrieve reviewed facts for an elliptical question.

    Never use prior assistant text as an authority, and never use prior history
    to authorize an operation or to assert a booking/payment is complete.
    """
    if not VAGUE_FOLLOWUP.fullmatch(message.strip()):
        return message
    for turn in reversed(history[-20:]):
        if turn.get('role') != 'user':
            continue
        previous = str(turn.get('content', '')).strip()
        if len(previous.split()) >= 3 and previous != message and not VAGUE_FOLLOWUP.fullmatch(previous):
            return f'{previous[:350]} {message}'
    return message


def recent_conversation(history: list[dict[str, Any]], count: int = 12) -> list[dict[str, str]]:
    """Limit the model's attention to the most recent complete turns.

    Conversation entries are untrusted dialogue, not instructions to tools.
    """
    out = []
    for item in history[-max(1, min(count, 20)):]:
        role = item.get('role')
        content = str(item.get('content', '')).strip()[:650]
        if role in ('user', 'assistant') and content:
            out.append({'role': role, 'content': content})
    return out
