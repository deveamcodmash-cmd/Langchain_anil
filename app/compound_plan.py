"""Plan multi-clause giving-plan edits as a single *non-financial* proposal.

A multi-step request is NOT multiple independent UI commands. Each clause is
interpreted separately; only narrow allowlisted draft operations are returned.
The Joomla UI validates and commits the whole operation atomically against a
fresh guarded draft snapshot. No money, account record, or checkout is changed.
"""
from __future__ import annotations

import re

from .schemas import ChatRequest, ChatResponse
from .plan_intelligence import classify_plan_command, validate_target

ALLOWED = frozenset({'remove_plan_item','update_plan_budget','adjust_plan_budget','rebalance_plan'})
QUESTION = re.compile(r'^\s*(?:what\s+(?:if|would|happens)|how\s+(?:do|can|would|should)|could\s+you\s+(?:explain|tell)|why)\b', re.I)
NEW_PLAN = re.compile(r'\b(?:new|another|different|replace)\s+(?:giving\s+)?(?:plan|campaigns?|causes?)\b', re.I)
CLAUSE_DELIMITER = re.compile(r'\s*(?:,(?!\d)\s*(?:and\s+)?|\s+and\s+(?:then\s+)?|\s+then\s+)\s*', re.I)


def parse_compound_plan(request: ChatRequest) -> ChatResponse | None:
    plan=request.current_plan
    message=request.message.strip()
    if not plan or len(plan.items)<1 or QUESTION.match(message) or NEW_PLAN.search(message):
        return None
    clauses=[c.strip(' .!') for c in CLAUSE_DELIMITER.split(message) if c.strip(' .!')]
    if not 2<=len(clauses)<=3:
        return None
    steps=[]
    for clause in clauses:
        action=classify_plan_command(clause)
        if not action or action.get('type') not in ALLOWED:
            return None
        if validate_target(action,plan):
            return None
        steps.append(action)
    # Enforce operations that can be simulated atomically, not a loosely
    # defined list where later steps change the meaning of earlier positions.
    types=[s['type'] for s in steps]
    if len(types)!=len(set(types)) or types.count('remove_plan_item')>1:
        return None
    if 'rebalance_plan' in types and types[-1]!='rebalance_plan':
        return None
    remaining=len(plan.items)-int('remove_plan_item' in types)
    if remaining<1:
        return ChatResponse(reply='That would leave your plan without a selected campaign. Would you like to keep one campaign or clear the whole draft?',
                            mode='clarification',agents_run=['Plan Transaction','Clarification'])
    budget=plan.budget
    for step in steps:
        typ=step['type']
        if typ=='update_plan_budget':
            if step.get('currency','CURRENT') not in {'CURRENT',plan.currency}:
                return ChatResponse(reply=f'Your existing plan uses {plan.currency}. I can keep it in that currency, or help you start a separate plan.',mode='clarification',agents_run=['Plan Transaction','Clarification'])
            budget=int(step['amount'])
        elif typ=='adjust_plan_budget':
            if step.get('currency','CURRENT') not in {'CURRENT',plan.currency}:
                return ChatResponse(reply=f'Your current plan uses {plan.currency}. Please choose a consistent currency before changing the total.',mode='clarification',agents_run=['Plan Transaction','Clarification'])
            budget+=int(step['delta'])
    if budget<remaining or budget>1_000_000_000:
        return ChatResponse(reply=f'Your draft will still contain {remaining} campaign(s). Please choose a total that allows at least one {plan.currency} unit per campaign.',mode='clarification',agents_run=['Plan Transaction','Clarification'])
    return ChatResponse(
        reply='I can make these updates together in your existing giving-plan draft. No payment will be made.',
        action_proposal={'type':'plan_transaction','steps':steps},
        agents_run=['Plan Context','Plan Transaction'],mode='action_proposed')

# Optional LLM planner for unfamiliar multi-clause language. It only generates
# candidate allowlisted draft steps; validator requires the actual visitor to
# have named each position and monetary amount. Never an action executor.
from typing import Literal
from pydantic import BaseModel, Field

class CandidateStep(BaseModel):
    type: Literal['remove_plan_item','update_plan_budget','adjust_plan_budget','rebalance_plan']
    position: int | None = Field(default=None,ge=1,le=10)
    amount: int | None = Field(default=None,ge=1,le=1000000000)
    delta: int | None = Field(default=None,ge=-1000000000,le=1000000000)
    currency: str = Field(default='CURRENT',max_length=7)

class CandidateTransaction(BaseModel):
    confident: bool = False
    steps: list[CandidateStep] = Field(default_factory=list,min_length=0,max_length=3)


def validate_candidate_transaction(request: ChatRequest, candidate: CandidateTransaction) -> ChatResponse | None:
    """Require independent evidence from user text for every monetary value and target."""
    if not request.current_plan or QUESTION.match(request.message) or NEW_PLAN.search(request.message):
        return None
    if not candidate.confident or not 2<=len(candidate.steps)<=3:
        return None
    from .plan_semantics import written_amounts, user_currency
    source=request.message
    amounts=written_amounts(source)
    named_positions=set()
    ordinals={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,
              'seventh':7,'eighth':8,'ninth':9,'tenth':10}
    for word,number in ordinals.items():
        if re.search(r'\b'+word+r'\b',source,re.I):named_positions.add(number)
    named_positions.update(int(x) for x in re.findall(r'\b(?:campaign|item|option)\s+(\d{1,2})\b',source,re.I))
    if re.search(r'\blast\s+(?:campaign|one|item)\b',source,re.I):
        named_positions.add(len(request.current_plan.items))
    given_currency=user_currency(source)
    steps=[]
    for item in candidate.steps:
        action=item.model_dump(exclude_none=True)
        typ=action['type']
        if typ=='remove_plan_item':
            if not re.search(r'\b(?:remove|drop|delete|exclude|take\s+out|ditch)\b',source,re.I):return None
            if action.get('position') not in named_positions:return None
        if typ=='update_plan_budget':
            if not re.search(r'\b(?:budget|total|spending|amount)\b',source,re.I):return None
            if action.get('amount') not in amounts:return None
        if typ=='adjust_plan_budget':
            if not re.search(r'\b(?:budget|total|spending|amount)\b',source,re.I):return None
            if not isinstance(action.get('delta'),int) or abs(action['delta']) not in amounts or action['delta']==0:return None
            if action['delta']<0 and not re.search(r'\b(?:decrease|reduce|lower|cut|down|subtract|less)\b',source,re.I):return None
            if action['delta']>0 and not re.search(r'\b(?:increase|raise|add|up|more)\b',source,re.I):return None
        if typ=='rebalance_plan' and not re.search(r'\b(?:equally|equal|evenly|rebalance|split|divide)\b',source,re.I):return None
        if given_currency and given_currency!=request.current_plan.currency:
            return None
        if action.get('currency','CURRENT') not in {'CURRENT',request.current_plan.currency}:return None
        action['currency']='CURRENT' if typ in {'update_plan_budget','adjust_plan_budget'} else action.get('currency','CURRENT')
        steps.append(action)
    # Reuse a single shared semantic validator by assembling a candidate in
    # source order and running the exact same action/target/budget checks.
    return _validate_steps(request,steps)


def _validate_steps(request:ChatRequest, steps:list[dict]) -> ChatResponse | None:
    plan=request.current_plan
    if not plan or not 2<=len(steps)<=3:return None
    types=[s['type'] for s in steps]
    if len(set(types))!=len(types) or 'rebalance_plan' in types and types[-1]!='rebalance_plan':return None
    budget=plan.budget
    remaining=len(plan.items)
    for step in steps:
        if step['type'] not in ALLOWED:return None
        if validate_target(step,plan):return None
        if step['type']=='remove_plan_item':remaining-=1
        elif step['type']=='update_plan_budget':budget=step['amount']
        elif step['type']=='adjust_plan_budget':budget+=step['delta']
    if remaining<1 or budget<remaining or budget>1000000000:return None
    return ChatResponse(reply='I can update the existing giving-plan draft using these steps together. No payment will be made.',
        action_proposal={'type':'plan_transaction','steps':steps},mode='action_proposed',agents_run=['Contextual Planner','Plan Transaction'])


def semantic_compound_plan(request: ChatRequest) -> ChatResponse | None:
    """Use the model only as a bounded interpreter when direct parsing missed."""
    import os
    if not request.current_plan or not request.current_plan.items or not os.getenv('OPENAI_API_KEY'):
        return None
    message=request.message
    if not re.search(r'\b(?:and|then|also)\b|,',message,re.I) or QUESTION.match(message) or NEW_PLAN.search(message):return None
    if not re.search(r'\b(?:plan|campaign|budget|total|spending|allocation)\b',message,re.I):return None
    if not re.search(r'\b(?:remove|drop|ditch|delete|exclude|update|change|adjust|lower|reduce|decrease|raise|increase|split|rebalance)\b',message,re.I):return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage,HumanMessage
        model=ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),temperature=0,
             timeout=18,max_retries=0).with_structured_output(CandidateTransaction)
        candidate=model.invoke([
          SystemMessage(content='Interpret the latest Filantrophy visitor sentence as a sequence of at most 3 permitted giving-plan DRAFT edits. ' 
            'Never use previous turns to invent an action. Only draft remove_plan_item (position explicitly named), ' 
            'update_plan_budget, adjust_plan_budget, or rebalance_plan. ' 
            'Every number and position must be explicitly present in the latest sentence. Currency CURRENT means preserve the current plan currency. ' 
            'Never save a plan, select a different campaign, book, pay, or interpret a hypothetical question as authorization. ' 
            'Choose confident=false if uncertain.'),
          HumanMessage(content=str({'latest_message':message,'plan_currency':request.current_plan.currency,
             'selected_positions':list(range(1,len(request.current_plan.items)+1))}))
        ])
        return validate_candidate_transaction(request,candidate)
    except Exception:
        return None


def ambiguous_multiple_edits(request:ChatRequest) -> bool:
    """Fail closed when a compound instruction cannot be interpreted safely.

    The ordinary single-action parser can wrongly turn 'remove the second and
    lower the overall budget to 9k' into an allocation edit on the second item.
    Never permit that fallthrough when at least two action clauses are visible.
    """
    if not request.current_plan or QUESTION.match(request.message) or NEW_PLAN.search(request.message):return False
    from .plan_semantics import written_amounts
    clauses=[c.strip() for c in CLAUSE_DELIMITER.split(request.message) if c.strip()]
    if len(clauses)<2:return False
    signals=0
    for clause in clauses:
        has_amount=bool(written_amounts(clause))
        ordinal=bool(re.search(r'\b(?:first|second|third|fourth|fifth|sixth|last|\d+(?:st|nd|rd|th))\b',clause,re.I))
        removal=bool(re.search(r'\b(?:remove|drop|delete|exclude|ditch)\b',clause,re.I)) and ordinal
        adjustment=has_amount and bool(re.search(r'\b(?:reduce|decrease|lower|cut|increase|raise|set|make|change|update|adjust|bring|rebalance)\b',clause,re.I))
        if removal or adjustment:signals+=1
    return signals>=2
