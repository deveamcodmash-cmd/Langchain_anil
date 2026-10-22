"""Contextual giving-plan resolver for references to previously displayed campaigns.

The model must not decide what "those three" refers to. The caller (Filantrophy)
provides the IDs it actually displayed in the previous verified response.
This module NEVER performs a payment or persists a giving plan.
"""
from __future__ import annotations

import re

from .schemas import ChatRequest, ChatResponse, SuggestedPlan, SuggestedAllocation

CURRENCY_CODES = ('NGN','USD','GBP','EUR','GHS','KES','ZAR','RWF','XOF','INR','CAD','AUD')
SYMBOL_CURRENCIES = {'₦':'NGN','$':'USD','£':'GBP','€':'EUR','₹':'INR'}
NUMBERS = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
NUM_WORD = '(?:' + '|'.join(NUMBERS) + r'|\d{1,2})'
REF = re.compile(
    r'\b(?:them|those|these|the ones|the above|the previous|just (?:shown|listed)|'
    r'(?:first|last)\s+(?:' + NUM_WORD + r')\b|'
    r'(?:' + NUM_WORD + r')\s+(?:of\s+)?(?:them|those|these)|'
    r'all\s+(?:of\s+)?(?:them|those|these|(?:the\s+)?(?:campaigns|causes)))\b', re.I)
PLAN = re.compile(r'\b(?:donat(?:e|ion|ing)|giv(?:e|ing)|add|allocat(?:e|ion)|split|distribut(?:e|ion)|contribut(?:e|ion)|support|plan)\b',re.I)
EXPLICIT_MONEY = re.compile(r'(?P<sign>₦|\$|£|€|₹)\s*(?P<amount>\d[\d,]*)|\b(?P<code>' + '|'.join(CURRENCY_CODES) + r')\s*(?P<prefixamount>\d[\d,]*)\b|\b(?P<suffixamount>\d[\d,]*)\s*(?P<suffixcode>' + '|'.join(CURRENCY_CODES) + r')\b',re.I)
VERB_AMOUNT = re.compile(r'\b(?:donate|give|split|allocate|contribute|budget|amount|total|donation|giving)\s+(?:(?:a|of|for|about|total|budget|amount|of\s+about)\s+)?(?P<amount>\d[\d,]*)\b',re.I)
COUNT = re.compile(r'\b(?P<count>' + NUM_WORD + r')\s+(?:of\s+)?(?:them|those|these)\b',re.I)
FIRST_LAST = re.compile(r'\b(?P<direction>first|last)\s+(?P<count>' + NUM_WORD + r')\b',re.I)

def _int(raw: str) -> int | None:
    # Reject malformed digit separators rather than misinterpreting monetary value.
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)',raw):
        return None
    number=int(raw.replace(',',''))
    return number if 1 <= number <= 1_000_000_000 else None

def _count(raw: str) -> int:
    return NUMBERS[raw.lower()] if raw.lower() in NUMBERS else int(raw)

def _amount_and_currency(message: str) -> tuple[int | None, str | None]:
    found=EXPLICIT_MONEY.search(message)
    if found:
        amount=_int(found.group('amount') or found.group('prefixamount') or found.group('suffixamount'))
        code = (found.group('code') or found.group('suffixcode') or SYMBOL_CURRENCIES.get(found.group('sign'), '')).upper()
        return amount, code
    match=VERB_AMOUNT.search(message)
    return (_int(match.group('amount')),None) if match else (None,None)

def contextual_plan(request: ChatRequest) -> ChatResponse | None:
    """Return a safe draft proposal/clarification for contextual instructions, if any.

    The list of previous IDs MUST originate from a server-side rendered result;
    it must never be accepted from unverified browser-supplied state.
    """
    message=request.message
    if not (REF.search(message) and PLAN.search(message)):
        return None
    ids=request.recent_campaign_ids
    if not ids:
        return ChatResponse(reply='Please show or select the campaigns you want to support first. Then I can create a giving plan using those exact campaigns.',mode='contextual_clarification',agents_run=['Context Resolver'])
    by_id={c.id:c for c in request.campaigns}
    if any(i not in by_id for i in ids):
        return ChatResponse(reply='One or more previously shown campaigns are no longer available for a giving plan. Please refresh the campaign results before proceeding.',mode='contextual_clarification',agents_run=['Context Resolver'])
    selected=list(ids)
    first_last=FIRST_LAST.search(message)
    count_match=COUNT.search(message)
    if first_last:
        count=_count(first_last.group('count'))
        if count>len(ids):
            return ChatResponse(reply=f'Only {len(ids)} campaigns were shown. Please choose from those campaigns or search for more.',mode='contextual_clarification',agents_run=['Context Resolver'])
        selected=ids[:count] if first_last.group('direction').lower()=='first' else ids[-count:]
    elif count_match:
        count=_count(count_match.group('count'))
        if count>len(ids):
            return ChatResponse(reply=f'Only {len(ids)} campaigns were shown. Please choose from those campaigns or search for more.',mode='contextual_clarification',agents_run=['Context Resolver'])
        if count<len(ids):
            return ChatResponse(reply=f'Which {count} of the {len(ids)} campaigns would you like to support? You can say “the first {count}” or name them.',mode='contextual_clarification',agents_run=['Context Resolver'])
    if len(selected)>10:
        return ChatResponse(reply='A single giving plan supports up to 10 campaigns. Please choose up to 10 of the campaigns you just viewed.',mode='contextual_clarification',agents_run=['Context Resolver'])
    currencies={by_id[i].currency for i in selected}
    if len(currencies)!=1:
        options=', '.join(sorted(currencies))
        return ChatResponse(reply=f'These campaigns use different currencies ({options}). One payment needs campaigns in the same currency. Please choose a currency or select campaigns that match.',mode='contextual_clarification',agents_run=['Context Resolver'])
    currency=next(iter(currencies))
    amount,requested_currency=_amount_and_currency(message)
    if amount is None:
        return ChatResponse(reply=f'How much would you like to donate to these {len(selected)} campaigns? They accept {currency}. No payment will be made until you review and confirm it.',mode='contextual_clarification',agents_run=['Context Resolver'])
    if requested_currency is not None and requested_currency!=currency:
        return ChatResponse(reply=f'The {len(selected)} campaigns you just viewed accept {currency}, but you requested {requested_currency}. I cannot silently change currencies. Would you like a {currency} giving plan, or should I find campaigns accepting {requested_currency}?',mode='contextual_clarification',agents_run=['Context Resolver'])
    if amount<len(selected):
        return ChatResponse(reply=f'The {currency} {amount:,} budget is too small to allocate a positive whole-number amount across {len(selected)} campaigns. Please increase the budget.',mode='contextual_clarification',agents_run=['Context Resolver'])
    per,extra=divmod(amount,len(selected))
    items=[SuggestedAllocation(id=id_,amount=per+(1 if i<extra else 0)) for i,id_ in enumerate(selected)]
    plan=SuggestedPlan(currency=currency,budget=amount,items=items)
    allocation=', '.join(f'{currency} {item.amount:,} to {by_id[item.id].title}' for item in items)
    inference=(f' I used {currency} because all {len(selected)} campaigns shown accept that currency.' if requested_currency is None else '')
    return ChatResponse(
        reply=(f'I prepared a {currency} {amount:,} giving plan for the {len(selected)} campaigns you just viewed: {allocation}.{inference} Review your plan and confirm the payment when ready. No payment has been made.'),
        plan_proposal=plan,mode='contextual_plan',agents_run=['Context Resolver','Giving Plan'],
    )
