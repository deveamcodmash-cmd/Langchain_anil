"""Resolve continuing giving-plan edits against the *current verified draft*.

A short follow-up like "yes" or "USD" is not a request to search the
campaign catalogue. It may complete the immediately preceding plan instruction,
but only when that instruction can be reconstructed from recent user messages.
All returned operations remain proposals; Joomla validates and applies them.
"""
from __future__ import annotations

import re
from .schemas import ChatRequest, ChatResponse
from .plan_intelligence import classify_plan_command, validate_target
from .intent_guard import parse_plan_action

CURRENCY_ONLY = re.compile(r'^\s*(usd|ngn|gbp|eur|inr|ghs|kes|zar|cad|aud|\$|₦|£|€|₹)\s*[.!]?\s*$', re.I)
CURRENCY_SYMBOLS = {'$': 'USD', '₦': 'NGN', '£': 'GBP', '€': 'EUR', '₹': 'INR'}
AFFIRMATIVE = re.compile(r'^\s*(?:yes|yeah|yep|okay|ok|sure|go ahead|do it|yes please|please do|adjust it|adjust them|recalculate|proceed|yes adjust(?: it| the amounts?)?)\s*[.!]?\s*$',re.I)
CONFIRM_WITH_NUMBER = re.compile(r'^\s*(?:yes|sure|okay|ok|please|go ahead)[\s,]+(?:adjust|change|update|reduce|decrease|set|make|recalculate)\b',re.I)


def action_response(action: dict) -> ChatResponse:
    """The browser, not this reply, decides whether an action succeeded."""
    return ChatResponse(
        reply='I can apply that change to your current giving-plan draft. No payment will be made.',
        action_proposal=action,mode='action_proposed',
        agents_run=['Plan Context','Plan Action'],
    )


def resolve_plan_followup(request: ChatRequest) -> ChatResponse | None:
    plan = request.current_plan
    if not plan or not plan.items:
        return None
    message = request.message.strip()
    currency = CURRENCY_ONLY.fullmatch(message)
    affirm = AFFIRMATIVE.fullmatch(message) or CONFIRM_WITH_NUMBER.match(message)
    if not (currency or affirm):
        return None
    if currency:
        requested = CURRENCY_SYMBOLS.get(currency.group(1),currency.group(1).upper())
        if requested != plan.currency:
            return ChatResponse(
                reply=f'Your current giving plan uses {plan.currency}. I can keep that plan as it is, or help you prepare a separate plan in {requested}. Which would you prefer?',
                mode='clarification',agents_run=['Plan Context','Clarification'],
            )
    # Only resolve a response to a recent request. Do not reinterpret an unrelated
    # older instruction just because the user typed "yes" in a new conversation.
    turns = request.history[-8:]
    last = turns[-1] if turns else None
    if not last or last.role != 'assistant':
        return None
    last_reply = last.content.lower()
    # Only a genuine outstanding question may be completed by a brief answer.
    # An acknowledged successful edit must never be replayed on a later "yes".
    if '?' not in last_reply and not re.search(r'\b(?:please confirm|please specify|choose a currency|which currency)\b',last_reply):
        if currency:
            return ChatResponse(reply=f'Your current giving plan uses {plan.currency}. What would you like to adjust?',mode='contextual_clarification',agents_run=['Plan Context'])
        return None
    if currency and not re.search(r'\bcurrenc(?:y|ies)\b|\b(?:usd|ngn|gbp|eur|inr)\b',last_reply):
        return ChatResponse(reply=f'Your existing giving plan uses {plan.currency}. What would you like to adjust?',mode='contextual_clarification',agents_run=['Plan Context'])
    # The most recent *user* instruction before the clarifying reply owns the
    # pending intent. Prefer an actual requested total over assistant guesses.
    previous_user = next((turn.content for turn in reversed(turns[:-1]) if turn.role == 'user'), '')
    command = classify_plan_command(previous_user) or parse_plan_action(previous_user)
    if command and command.get('type') == 'update_plan_budget':
        if plan.budget == command['amount']:
            return ChatResponse(reply=f'Your giving plan already totals {plan.currency} {plan.budget:,}. Your selected campaigns are unchanged.',mode='contextual_clarification',agents_run=['Plan Context'])
        problem=validate_target(command,plan)
        if problem:
            return ChatResponse(reply=problem,mode='clarification',agents_run=['Plan Context','Clarification'])
        return action_response({'type':'update_plan_budget','amount':command['amount'],'currency':plan.currency})
    if currency:
        return ChatResponse(reply=f'Your giving plan already uses {plan.currency}. Tell me the budget you would like to use and I can update the draft.',mode='contextual_clarification',agents_run=['Plan Context'])
    return None
