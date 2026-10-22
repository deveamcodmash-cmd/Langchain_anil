"""Conservative, fast Filantrophy scope guard and structured action parsing.

The guard only refuses clearly off-topic requests. All decisions that could
change money or data are separately validated by the platform backend.
"""
import re
from typing import Any

OFF_TOPIC = [
    r'\b(best time to sleep|sleep schedule|how many hours? (?:should i|to) sleep)\b',
    r'\b(who is (?:the )?joker|who is batman|who is spiderman)\b',
    r'\b(write (?:me )?(?:python|javascript|php|sql) code|debug (?:this )?code)\b',
    r'\b(recipe for|football scores?|stock market forecast|tell me a joke)\b',
    r'\b(who (?:is|was) (?:taylor swift|ronaldo|spider[- ]?man)|solve (?:this )?algebra|write (?:me )?a poem)\b',
]
DOMAIN = re.compile(r'\b(filantrophy|donat(?:e|ion|ions|ing)|giv(?:e|ing)|campaigns?|causes?|healthcare campaign|education campaign|volunteering|volunteers?|charit(?:y|ies)|payment|receipt|refund|checkout|fundrais(?:e|ing)|impact|support|account|plan|budget|allocat(?:e|ion)|contribut(?:e|ion)|ngo|organis(?:e|er|ation)|corporate giving|csr|service providers?|service booking|book (?:a|an) (?:service|appointment)|events?|event (?:registrations?|bookings?|organiser|organizer)|rankings?|attendance|following|followers?)\b', re.I)
CODE_MARKERS = re.compile(r'(?:<\?php|\$config\[|RuntimeException\s*\(|\bfunction\s+\w+\s*\(|\bimport\s+os\b|\bSELECT\s+\*\s+FROM\b)', re.I)
AMOUNT = r'(?:₦|ngn\s*|\$|usd\s*|£|gbp\s*)([\d,]+)'

def assess(message: str) -> str:
    s=message.strip().lower()
    if CODE_MARKERS.search(message) and not re.search(r'\b(error|problem|support|report|security|breach|suspicious)\b', s):
        return 'off_topic'
    if DOMAIN.search(s):
        return 'in_scope'
    if any(re.search(pattern,s,re.I) for pattern in OFF_TOPIC):
        return 'off_topic'
    return 'uncertain'

def parse_plan_action(message: str) -> dict[str,Any] | None:
    """Parse safe draft operations. No payment or database operation is executed here."""
    s=message.strip().lower()
    if re.search(r'\b(?:undo|revert)\s+(?:the\s+)?(?:last\s+)?(?:change|action|that)\b|^undo[.! ]*$',s):
        return {'type':'undo_plan_change'}
    if re.search(r'\b(?:remove|clear|reset|delete)\s+(?:all\s+)?(?:the\s+)?(?:existing\s+)?(?:my\s+)?(?:giving\s+)?plan\b',s):
        return {'type':'clear_plan','requires_confirmation':True}
    match=re.search(r'\b(?:change|update|set|increase|decrease|make)\s+(?:my\s+|the\s+|it\s+|total\s+|donation\s+|giving\s+|plan\s+|budget\s+|amount\s+|to\s+|at\s+)*?(?:budget|amount|total)?\s*(?:to|at|as|=)?\s*'+AMOUNT+r'\b',s)
    if match:
        amount=int(match.group(1).replace(',',''))
        currency='NGN' if ('₦' in match.group(0) or 'ngn' in match.group(0)) else ('GBP' if '£' in match.group(0) or 'gbp' in match.group(0) else 'USD')
        if 1<=amount<=1000000000:
            return {'type':'update_plan_budget','amount':amount,'currency':currency}
    # Currency omitted: apply to the current draft currency, never guess a conversion.
    match=re.search(r'\b(?:change|update|set|make)\s+(?:(?:my|the|current|donation|giving|plan|total)\s+)*(?:budget|amount|total)\s+(?:to|at|as)\s*([\d,]+)\b',s)
    if match:
        amount=int(match.group(1).replace(',',''))
        if 1<=amount<=1000000000:
            return {'type':'update_plan_budget','amount':amount,'currency':'CURRENT'}
    match=re.search(r'\b(?:remove|delete)\s+(?:the\s+)?(first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)\s+campaign\b',s)
    if match:
        word=match.group(1)
        ordinal={'first':1,'second':2,'third':3,'fourth':4,'fifth':5}.get(word,int(re.match(r'\d+',word).group()) if re.match(r'\d+',word) else 0)
        return {'type':'remove_plan_item','position':ordinal}
    match=re.search(r'\b(?:allocate|set|change|make)\s*'+AMOUNT+r'\s+(?:to|for)\s+(?:the\s+)?(first|second|third|fourth|fifth)\s+campaign\b',s)
    if match:
        return {'type':'update_plan_allocation','amount':int(match.group(1).replace(',','')),'position':{'first':1,'second':2,'third':3,'fourth':4,'fifth':5}[match.group(2)]}
    return None
