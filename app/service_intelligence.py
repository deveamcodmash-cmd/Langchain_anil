"""Deterministic, catalogue-grounded Filantrophy service search.

An LLM must never convert an unknown service title into a made-up listing or
misroute a service search to donation campaigns. Public records remain supplied
by the authenticated Filantrophy gateway, not fetched from the LLM.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Iterable

# Strong signals are deliberately specific; general "health" and "help" are not.
SERVICE_SIGNALS = re.compile(
    r'\b(?:services?|service providers?|appointments?|bookings?|sessions?|'
    r'physio|physiotherap(?:y|ist|ists)|physical therapy|massage|massages|'
    r'yoga|meditation|wellness|spa|pilates|chiropract(?:ic|or)|'
    r'acupuncture|nutrition(?:ist)?|counsel(?:l)?ing|'
    r'dental|dentist|fitness|personal training|therapy|therapist|'
    r'consultation|treatments?|rehabilitation|diagnostics?|'
    r'checkups?|check-ups?|clinic|clinics)\b', re.I
)
EXPLICIT_CAMPAIGN = re.compile(r'\b(?:campaigns?|causes?|fundrais(?:e|er|ing)|giving plans?|donat(?:e|ions?|ing))\b', re.I)
INTENT = re.compile(r'\b(?:find|show|list|search|recommend|explore|discover|need|want|looking|available|book|reserve|schedule|where|see|give|provide)\b', re.I)
STOP = frozenset('''show find list search recommend explore discover need want looking me you i we our please kindly the this that those it is are any some all available availability on in at for of to with about regarding related concerning sessions session service services listing listings catalogue catalog directory provider providers booking book appointment appointments and or near around here now today tomorrow next filantrophy platform website giving give tell details info information something type types see can could would do have got get more yes sure ok okay there which what from my your offer offers offering offerings currently showtimes free paid costs cost how much price prices able a an as currently thanks thank events event workshops workshop volunteering volunteer opportunity opportunities one two three four five six seven eight nine ten'''.split())


def normalize_tokens(message: str) -> list[str]:
    normalized = unicodedata.normalize('NFKD', message).casefold()
    words = re.findall(r'[a-z0-9]+', normalized)
    return list(dict.fromkeys(w for w in words if len(w) >= 3 and w not in STOP and not w.isdigit()))


def _contains(haystack: str, token: str) -> bool:
    if token in haystack:
        return True
    if len(token) >= 5:
        # Very conservative plural/format tolerance, never fuzzy-match arbitrary records.
        stem = token[:-1] if token.endswith('s') else token
        return len(stem) >= 5 and stem in haystack
    return False


def requested_location(message: str) -> str:
    match = re.search(r'\b(?:in|around|near)\s+([a-z][a-z .-]{1,60})', message, re.I)
    if not match:
        return ''
    phrase = re.split(r'[,;?.!]|\b(?:with|that|and|which|for|from|please)\b',match.group(1),maxsplit=1,flags=re.I)[0]
    phrase = phrase.strip().lower()
    if phrase in {'me','here','filantrophy','the platform','the website','my area','the area','this city'} or phrase.startswith(('filantrophy ', 'the platform ')):
        return ''
    return phrase


def relevant_services(message: str, records: Iterable, limit: int = 30) -> list:
    """Rank matching service records; require a meaningful textual match.

    A generic "show services" request may return the public catalogue.
    A specific request never falls back to unrelated services.
    """
    location = requested_location(message)
    location_terms = normalize_tokens(location)
    terms = [t for t in normalize_tokens(message) if t not in location_terms]
    records = list(records)
    if location_terms:
        records = [r for r in records if all(t in str(r.location or '').casefold() for t in location_terms)]
    if not terms:
        return [r for r in records if getattr(r,'kind',None)=='service'][:limit]
    scored = []
    for row in records:
        if getattr(row, 'kind', None) != 'service':
            continue
        title = str(row.title or '').casefold()
        summary = str(row.summary or '').casefold()
        location = str(row.location or '').casefold()
        high = sum(1 for w in terms if _contains(title, w))
        secondary = sum(1 for w in terms if _contains(summary, w))
        low = sum(1 for w in terms if _contains(location, w))
        # At least one subject keyword must match title or category/description.
        # Avoid returning a service just because a requested city matched.
        if high + secondary == 0:
            continue
        score = high * 10 + secondary * 4 + low
        # Stronger matches first; stable ordering among ties.
        scored.append((-score, row))
    scored.sort(key=lambda pair: pair[0])
    return [row for _, row in scored[:limit]]


def is_service_request(message: str, records: Iterable) -> bool:
    """Recognize explicit service intent OR named real service listings.

    Campaign intent wins for an explicit campaign request, even when its text
    also contains therapy or healthcare language.
    """
    # Distinguish questions about *account types* from a request to book a
    # provider's service. Otherwise a role comparison can wrongly display an
    # unrelated Food Distribution result because it contains "provider".
    from .site_guidance import is_site_explanation
    if is_site_explanation(message):
        return False
    if EXPLICIT_CAMPAIGN.search(message):
        return False
    # A service name coincidentally matching a movie, education or help request
    # must never override an explicit non-platform subject.
    from .dialogue_intelligence import general_only_question, GUIDE_BOOKING
    if general_only_question(message) or GUIDE_BOOKING.search(message):
        return False
    # Educational questions about a therapy, clinic, or service are different
    # from searching the published directory. The model should explain them.
    if re.search(r'^\s*(?:what\s+(?:is|are|does)|why\b|how\s+(?:to|do|does|can)|explain\b|define\b|meaning\s+of\b|tell\s+me\s+(?:about|how))', message, re.I) \
            and not re.search(r'\b(?:find|show|list|search|available)\b', message, re.I):
        return False
    if SERVICE_SIGNALS.search(message):
        # An instructional mention of a booking form is not a discovery query.
        return not bool(re.search(r'^\s*(?:guide|help|explain|how)\b',message,re.I) and not re.search(r'\b(?:find|show|search|list|available)\b',message,re.I))
    # Example: "Show Serenity Wellness Centre" where a matching service is in
    # the trusted, already-loaded catalogue. Don't do this for bare greetings.
    if not INTENT.search(message):
        return False
    terms = normalize_tokens(message)
    if not terms:
        return False
    return bool(relevant_services(message, [r for r in records if getattr(r,'kind',None)=='service'], 1))
