"""Catalogue-backed, read-only search across platform domains.

Every returned item must come from authenticated Filantrophy data. No model can
invent a service, booking slot, provider, price or booking confirmation.
"""
from __future__ import annotations
import re
from .schemas import ChatRequest, ChatResponse
from .service_intelligence import is_service_request, relevant_services, normalize_tokens

DOMAINS = {
    'event': re.compile(r'\b(events?|workshops?|conferences?|event registrations?)\b', re.I),
    'volunteering': re.compile(r'\b(volunteer|volunteering|opportunities|volunteer role)\b', re.I),
}
INTENT = re.compile(r'\b(find|show|search|list|recommend|explore|discover|near|available|where|looking|want|need)\b', re.I)

def _requested_limit(message: str) -> int:
    if re.search(r'\b(?:all|every)\b', message, re.I):
        return 30
    match = re.search(r'\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:matching\s+|available\s+|published\s+)*(?:events?|services?|appointments?|sessions?|volunteer(?:ing)?\s+opportunities?)\b', message, re.I)
    if not match:
        match = re.search(r'\b(?:show|find|list|give)\s+(?:me\s+)?(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\b', message, re.I)
    if match:
        numbers = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
        count = numbers.get(match.group(1).casefold())
        return max(1, min(30, count if count is not None else int(match.group(1))))
    return 10


def resource_search(request: ChatRequest) -> ChatResponse | None:
    message = request.message
    # Only run catalogue discovery for a genuine search or booking request.
    # A general educational question mentioning "service" is not automatically
    # a request to search the service directory.
    service = is_service_request(message, request.resources)
    if service:
        eligible = [r for r in request.resources if r.kind == 'service']
        ranked = relevant_services(message, eligible, 80)
        result = ranked[:_requested_limit(message)]
        if result:
            message_text = f'I found {len(result)} matching {"service" if len(result)==1 else "services"}. Select View Details or Book Now to continue.'
        else:
            # Do not claim there is no service on Filantrophy: the public catalogue
            # may be down or partially loaded, and the service could be elsewhere.
            message_text = ('Are you looking for sexual-health care, relationship counselling, or a different type of service? '
                            'I can check the published Services directory once we narrow that down.'
                            if re.search(r'\bsex\b', message, re.I)
                            else 'This search has not surfaced a matching service in the current listings. Try a more specific service specialty or location, or explore the Services directory.')
        return ChatResponse(reply=message_text, resources=result, resource_result_ids=[int(r.id) for r in ranked], agents_run=['Service Discovery'], mode='platform_search')
    if not INTENT.search(message):
        return None
    kinds=[name for name, pat in DOMAINS.items() if pat.search(message)]
    if not kinds or re.search(r'\bcampaigns?|causes?\b',message,re.I):
        return None
    candidates=[r for r in request.resources if r.kind in kinds]
    words=normalize_tokens(message)
    if words:
        scored=[]
        for row in candidates:
            hay=' '.join((row.title,row.location,row.summary)).casefold()
            score=sum(w in hay for w in words)
            if score:
                scored.append((-score,row))
        scored.sort(key=lambda p:p[0])
        candidates=[r for _,r in scored]
    found=candidates[:_requested_limit(message)]
    if not found:
        reply='This search has not surfaced a matching published listing. You can try another category or location, or explore the currently published opportunities.'
    else:
        reply=f'I found {len(found)} matching listings. Select one to view its details.'
    return ChatResponse(reply=reply,resources=found,agents_run=['Platform Search'],mode='platform_search')
