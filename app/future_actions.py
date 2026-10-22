"""Honest fallback for platform integrations not yet connected to AI tools."""
from __future__ import annotations
import re

FUTURE_ACTIONS = (
    (r'\b(?:book|reserve|schedule)\b.{0,50}\b(?:service|appointment|session|consultation)\b',
     'I can help you find an available service and open its booking form. Choose a service, select Book Now, and review the details before confirming. I cannot confirm a booking without the platform’s booking confirmation.'),
    (r'\b(?:register|sign\s*up|enrol|enroll)\b.{0,50}\b(?:event|workshop|conference)\b',
     'You can register through the Events section, where available event details and registration steps are shown. This chat can help you find the right event.'),
    (r'\b(?:apply|sign\s*up)\b.{0,50}\b(?:volunteering|volunteer opportunity|volunteer role)\b',
     'You can apply through the Volunteering section. I can help you explore published opportunities and choose one to review.'),
    (r'\b(?:publish|delete|archive|approve)\b.{0,50}\b(?:campaign|service|event|organisation)\b',
     'Your authorised Filantrophy dashboard is the place to manage publishing and administrative changes. I can help you locate the relevant section.'),
)


def unsupported_action_reply(message: str) -> str | None:
    for pattern, reply in FUTURE_ACTIONS:
        if re.search(pattern,message,re.IGNORECASE):
            return reply
    return None
