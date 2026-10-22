"""Grounded multiple-step campaign planning without model-invented identities.

Only draft changes or validated plan proposals are produced. No payments occur.
"""
from __future__ import annotations
import re
from .followup import _amount_and_currency
from .schemas import ChatRequest,ChatResponse,SuggestedPlan,SuggestedAllocation

CAUSE_ALIASES={
    'healthcare':('healthcare','health','clinic','medical','maternal'),
    'education':('education','school','learning','literacy'),
    'water':('water','sanitation'),
    'food':('food','hunger','nutrition','meal'),
    'environment':('environment','climate','tree'),
}
WORD_NUMS={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
COUNT_WORD=r'(?:\d{1,2}|'+ '|'.join(WORD_NUMS)+r')'

def count(token:str)->int:
    return int(token) if token.isdigit() else WORD_NUMS.get(token.lower(),0)

def selected_cause(message:str)->str|None:
    lower=message.lower()
    for key,words in CAUSE_ALIASES.items():
        if any(re.search(r'\b'+re.escape(w)+r'\b',lower) for w in words):return key
    return None

def multi_step(request:ChatRequest)->ChatResponse|None:
    msg=request.message.lower()
    candidates=request.campaigns
    cause=selected_cause(msg)
    # Append a number of matching campaigns to a currently selected plan.
    add=re.search(r'\b(?:add|include|select)\s+(?P<count>'+COUNT_WORD+r')\s+(?:more|additional|extra)\s+(?:\w+\s+){0,2}?(?:campaigns?|causes?)\b',msg)
    if add and request.current_plan and request.current_plan.items:
        qty=count(add.group('count'))
        plan=request.current_plan
        existing={x.id for x in plan.items}
        if len(existing)+qty>10:
            return ChatResponse(reply='A giving plan can contain up to ten campaigns. Please remove some selections before adding more.',mode='clarification',agents_run=['Multi-Step Planner'])
        eligible=[]
        for c in candidates:
            if c.id in existing or c.currency!=plan.currency:continue
            if cause and cause not in (c.title+' '+c.category+' '+c.summary).lower():continue
            eligible.append(c)
        selected=eligible[:qty]
        if len(selected)<qty:
            return ChatResponse(reply=f'I found only {len(selected)} additional eligible {cause or ""} campaign(s) using {plan.currency}. Would you like to add those instead?',mode='clarification',agents_run=['Multi-Step Planner'])
        return ChatResponse(reply=f'Adding {qty} matching campaign(s) to your existing giving plan. Please review the new allocations.',
            action_proposal={'type':'append_plan_campaigns','campaign_ids':[c.id for c in selected],'currency':plan.currency},
            agents_run=['Campaign Discovery','Multi-Step Planner'],mode='action_proposed')

    if not candidates or not re.search(r'\b(?:donate|donation|give|giving|allocate|split|distribute|budget|support)\b',msg):return None
    amount,currency=_amount_and_currency(msg)
    if amount is None:return None
    if not re.search(r'\b(?:campaigns?|causes?|healthcare|education|school|water|food|environment|medical|children)\b',msg):return None
    # Explicit queries listing several cause types should go to the LangGraph
    # supervisor rather than silently optimizing for the first cause mentioned.
    cause_matches=[key for key,words in CAUSE_ALIASES.items() if any(re.search(r'\b'+re.escape(w)+r'\b',msg) for w in words)]
    if len(cause_matches)>1:return None
    matches=[c for c in candidates if not cause or any(w in (c.title+' '+c.category+' '+c.summary).lower() for w in CAUSE_ALIASES[cause])]
    if not matches:return ChatResponse(reply='This search did not return a matching published cause in the current results. We can try a related topic or another location.',mode='clarification',agents_run=['Campaign Discovery'])
    selected_match=re.search(r'\b(?:select|choose|pick)\s+(?:the\s+)?(?:top\s+|first\s+)?(?P<n>'+COUNT_WORD+r')\b',msg)
    numbered=re.search(r'\b(?P<n>'+COUNT_WORD+r')\s+(?:matching\s+)?(?:\w+\s+)?(?:campaigns?|causes?)\b',msg)
    requested=count(selected_match.group('n')) if selected_match else count(numbered.group('n')) if numbered else min(3,len(matches))
    if requested>10:
        return ChatResponse(reply='A single giving plan supports up to ten campaigns. Please choose up to ten.',mode='clarification',agents_run=['Multi-Step Planner'])
    if requested>len(matches):
        return ChatResponse(reply=f'I found only {len(matches)} eligible matching campaigns. Would you like to use those?',mode='clarification',agents_run=['Multi-Step Planner'])
    chosen=matches[:requested]
    currencies={c.currency for c in chosen}
    if len(currencies)!=1:
        return ChatResponse(reply='The matching campaigns have different currencies. Choose campaigns using one currency for a single payment.',mode='clarification',agents_run=['Multi-Step Planner'])
    actual=next(iter(currencies))
    if currency and currency!=actual:
        return ChatResponse(reply=f'These campaigns use {actual}, but you requested {currency}. Would you prefer matching-currency campaigns or a {actual} plan?',mode='clarification',agents_run=['Multi-Step Planner'])
    if amount<requested:
        return ChatResponse(reply='The amount is too small to allocate a positive whole-number value to every campaign.',mode='clarification',agents_run=['Multi-Step Planner'])
    each,remainder=divmod(amount,requested)
    proposal=SuggestedPlan(currency=actual,budget=amount,items=[SuggestedAllocation(id=c.id,amount=each+(1 if i<remainder else 0)) for i,c in enumerate(chosen)])
    return ChatResponse(reply=f'I prepared a {actual} {amount:,} draft across {requested} {cause or "matching"} campaign(s). Review the amounts before continuing. No payment has been made.',
        plan_proposal=proposal,campaign_ids=[c.id for c in chosen],agents_run=['Campaign Discovery','Multi-Step Planner'],mode='multi_step_plan')
