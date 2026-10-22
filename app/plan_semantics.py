"""Model-assisted intent interpretation for previously unknown giving-plan phrasing.

LLM output NEVER executes a transaction. Only a narrow, auditable action type can
reach Joomla, with numerical values anchored in the latest user message and
campaign position resolved against the verified current plan.
"""
from __future__ import annotations

import os
import re
from typing import Literal

from pydantic import BaseModel, Field
from .schemas import ChatRequest, ChatResponse
from .plan_context import action_response
from .plan_intelligence import validate_target

class PlanInterpretation(BaseModel):
    action: Literal['none','set_total','change_total_by','equal_split','remove_selected','set_selected_amount','adjust_selected_by'] = 'none'
    amount: int | None = Field(default=None,ge=1,le=1000000000)
    direction: Literal['increase','decrease'] = 'increase'
    position: int | None = Field(default=None,ge=1,le=10)
    currency: str | None = Field(default=None,max_length=3)
    confident: bool = False

# Only invoke the language model for real draft-edit intents. Asking how a
# donation works is NOT permission to change a draft.
EDIT_VERB=re.compile(r'\b(?:adjust|modify|change|update|lower|reduce|decrease|cut|raise|increase|set|make|rebalance|redistribute|split|divide|remove|drop|assign)\b',re.I)
PLAN_CONTEXT=re.compile(r'\b(?:budget|total|allocation|plan|amount|first|second|third|fourth|last)\b',re.I)
MONEY_TOKEN=re.compile(r'(?<![\w])(?:\d{1,3}(?:,\d{3})+|\d{1,9})(?:\s*[kK])?(?!\w)')
SYMBOLS={'$':'USD','₦':'NGN','£':'GBP','€':'EUR','₹':'INR'}
CURRENCY_CODES=('USD','NGN','GBP','EUR','INR','GHS','KES','ZAR','CAD','AUD')


def written_amounts(message: str) -> set[int]:
    values=set()
    for match in MONEY_TOKEN.finditer(message):
        text=match.group().lower().replace(',','').replace(' ','')
        amount=int(text[:-1])*1000 if text.endswith('k') else int(text)
        if 1<=amount<=1000000000:values.add(amount)
    return values


def user_currency(message: str) -> str | None:
    for symbol,currency in SYMBOLS.items():
        if symbol in message:return currency
    m=re.search(r'\b(?:'+('|'.join(CURRENCY_CODES))+r')\b',message,re.I)
    return m.group().upper() if m else None


def decode_safe_interpretation(request: ChatRequest, parsed: PlanInterpretation) -> ChatResponse | None:
    plan=request.current_plan
    if not plan or not plan.items or not parsed.confident or parsed.action=='none':return None
    latest=request.message
    if not (EDIT_VERB.search(latest) and PLAN_CONTEXT.search(latest)):return None
    # Requests for a *different* plan are not edits to the selected campaigns.
    if re.search(r'\b(?:new|another|different|replace)\s+(?:giving\s+)?(?:plan|campaigns?|causes?)\b',latest,re.I):return None
    # Educational questions about making changes are not instructions.
    if re.match(r'^\s*(?:how\s+(?:do|can|should|would)\s+i|what\s+(?:happens|if|is)|why)\b',latest,re.I):return None
    # A model cannot select an arbitrary ordinal that the visitor never named.
    if parsed.action in {'remove_selected','set_selected_amount','adjust_selected_by'}:
        written_positions={int(x) for x in re.findall(r'\b(?:campaign|option|item|number)\s+(\d{1,2})\b',latest,re.I)}
        written_positions.update(int(x) for x in re.findall(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:campaign|option|item|one)\b',latest,re.I))
        names={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7,'eighth':8,'ninth':9,'tenth':10}
        for word,index in names.items():
            if re.search(r'\b'+word+r'\b',latest,re.I):written_positions.add(index)
        if re.search(r'\blast\s+(?:campaign|option|item|one)\b',latest,re.I):written_positions.add(len(plan.items))
        if parsed.position not in written_positions:return None
    if parsed.action=='equal_split':
        return action_response({'type':'rebalance_plan'})
    amounts=written_amounts(latest)
    if parsed.action!='remove_selected' and (parsed.amount is None or parsed.amount not in amounts):return None
    supplied=user_currency(latest)
    if supplied and supplied != plan.currency:
        return ChatResponse(reply=f'Your current giving plan uses {plan.currency}. Would you like to continue with that currency, or start another plan in {supplied}?',mode='clarification',agents_run=['Plan Context','Clarification'])
    action=None
    if parsed.action=='set_total':action={'type':'update_plan_budget','amount':parsed.amount,'currency':'CURRENT'}
    elif parsed.action=='change_total_by':action={'type':'adjust_plan_budget','delta':parsed.amount if parsed.direction=='increase' else -parsed.amount,'currency':'CURRENT'}
    elif parsed.action=='remove_selected' and parsed.position:action={'type':'remove_plan_item','position':parsed.position}
    elif parsed.action=='set_selected_amount' and parsed.position:action={'type':'update_plan_allocation','position':parsed.position,'amount':parsed.amount,'currency':'CURRENT'}
    elif parsed.action=='adjust_selected_by' and parsed.position:action={'type':'adjust_plan_allocation','position':parsed.position,'delta':parsed.amount if parsed.direction=='increase' else -parsed.amount,'currency':'CURRENT'}
    if not action:return None
    problem=validate_target(action,plan)
    if problem:return ChatResponse(reply=problem,mode='clarification',agents_run=['Plan Context','Clarification'])
    return action_response(action)


def semantic_plan_edit(request: ChatRequest) -> ChatResponse | None:
    """A bounded structured classifier, tried only after explicit commands fail.

    Does not let a model choose monetary values absent from the user's text.
    Network/provider errors fall back to normal conversation, not auto-commit.
    """
    if not request.current_plan or not request.current_plan.items:return None
    message=request.message
    if not (EDIT_VERB.search(message) and PLAN_CONTEXT.search(message)):return None
    if not os.getenv('OPENAI_API_KEY'):return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        model=ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),temperature=0,
            timeout=18,max_retries=0).with_structured_output(PlanInterpretation)
        parsed=model.invoke([
            SystemMessage(content='Classify the CURRENT visitor request about a giving plan, not the assistant replies. '
                'Only classify a clearly requested draft change. Use none if the user is asking a question or merely discussing an option. '
                'Set the amount ONLY to a number explicitly written in the latest visitor message; never use numbers from history, '
                'never infer the currency, and never invent campaign IDs. When in doubt choose none and confident=false. '
                'Never propose a payment, transfer or account save.'),
            HumanMessage(content=str({'latest_message':message,
                'current_plan':request.current_plan.model_dump(),
                'recent_history_for_reference_only':[m.model_dump() for m in request.history[-6:]]}))
        ])
        return decode_safe_interpretation(request,parsed)
    except Exception:
        return None
