"""Deterministic draft-only commands for the Filantrophy assistant.

The model never selects a campaign ID for a positional edit. Positions refer to
ordered, server-validated *current plan* entries. No checkout tools are exposed.
"""
from __future__ import annotations
import re
from typing import Any

ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
            'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10, 'last': -1}
ORDER = r'(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last|\d{1,2}(?:st|nd|rd|th)?)'
NUMBER = r'(?:(?P<currency>₦|\$|£|€|₹|(?i:NGN|USD|GBP|EUR|INR))\s*)?(?P<amount>\d{1,3}(?:,\d{3})+|\d{1,9})'
CURRENCIES={'₦':'NGN','$':'USD','£':'GBP','€':'EUR','₹':'INR'}
CAUSE = re.compile(r'\b(healthcare|health|education|school|water|food|hunger|environment|children|medical|relief)\b', re.I)

def ordinal(text: str) -> int:
    text=text.lower(); match=re.match(r'\d+',text)
    return int(match.group()) if match else ORDINALS.get(text, 0)

def amount_from(match: re.Match) -> tuple[int|None,str]:
    raw=match.group('amount').replace(',','')
    n=int(raw)
    cur=(match.groupdict().get('currency') or 'CURRENT').upper()
    return (n if 1<=n<=1_000_000_000 else None, CURRENCIES.get(cur,cur))

def classify_plan_command(message: str) -> dict[str,Any] | None:
    s=' '.join(message.strip().split()).lower()
    if re.search(r'\b(?:undo|revert|go back)\b',s) and not re.search(r'\brefund\b',s):
        return {'type':'undo_plan_change'}
    if re.search(r'\b(?:clear|reset|remove|delete)\s+(?:(?:all|the|my|current|existing|giving)\s+)*plan\b',s):
        return {'type':'clear_plan','requires_confirmation':True}
    # 'add 100 to the second campaign', 'in the second campaign add 100', etc.
    pos_before = re.search(r'\b(?:the\s+)?(?P<pos>'+ORDER+r')\s+(?:selected\s+)?(?:campaign|cause|one)\b',s)
    if pos_before:
        position=ordinal(pos_before.group('pos'))
        # remove first campaign, remove last one; but don't interpret "remove all"
        if re.search(r'\b(remove|delete|drop)\b',s) and not re.search(r'\b(add|increase|reduce|decrease|set|make|allocate)\b',s):
            return {'type':'remove_plan_item','position':position}
        delta_match=re.search(r'\b(?P<verb>add|increase|raise|reduce|decrease|subtract|deduct)\b(?:\s+(?:it|the\s+allocation|amount|by|with|to))?\s+'+NUMBER+r'\b',s)
        # 'increase the second campaign by 100'
        if not delta_match:
            delta_match=re.search(r'\b(?P<verb>add|increase|raise|reduce|decrease|subtract|deduct)\b.*?(?:\bby\s+|\bwith\s+)'+NUMBER+r'\b',s)
        if delta_match:
            val,cur=amount_from(delta_match)
            if val is not None:
                sign=-1 if delta_match.group('verb') in {'reduce','decrease','subtract','deduct'} else 1
                return {'type':'adjust_plan_allocation','position':position,'delta':sign*val,'currency':cur}
        set_match=re.search(r'\b(?:set|make|change|allocate|assign)\b(?:.*?\b(?:to|at|as|=)\b\s*|\s+)'+NUMBER+r'\b',s)
        if not set_match:
            set_match=re.search(r'\b(?:set|make|change|allocate|assign)\b.*?\b(?:campaign|cause|one)\s*'+NUMBER+r'\b',s)
        if set_match:
            val,cur=amount_from(set_match)
            if val is not None:
                return {'type':'update_plan_allocation','position':position,'amount':val,'currency':cur}
        # 'second campaign to 300' with no verb
        trailing=re.search(r'\b(?:to|at|=)\s*'+NUMBER+r'\b',s)
        if trailing:
            val,cur=amount_from(trailing)
            if val is not None:
                return {'type':'update_plan_allocation','position':position,'amount':val,'currency':cur}
    if re.search(r'\b(?:split|divide|redistribute|share)\s+(?:the\s+)?(?:rest|remaining|remainder)\s+equally\b',s):
        return {'type':'distribute_remaining'}
    if re.search(r'\b(?:split|divide|distribute|rebalance)\s+(?:the\s+)?(?:plan|budget|amount|allocations?|money|it)?\s*equally\b',s):
        return {'type':'rebalance_plan'}
    # A target total is different from a delta. Real examples: "decrease the
    # total budget to 9000", "please reduce my budget to $9,000", and
    # "yes adjust the amount and decrease to 9000". The original parser only
    # recognised set/make/change, causing these to fall through to discovery.
    target_total=re.search(
        r'\b(?:set|make|change|update|reduce|decrease|lower|cut|raise|increase)\b'
        r'(?:(?!\b(?:first|second|third|fourth|campaign|allocation)\b).){0,75}?'
        r'\b(?:total(?:\s+(?:budget|amount))?|budget|giving\s+plan\s+budget|donation\s+amount)\s+'
        r'(?:to|at|as|=)\s*'+NUMBER+r'\b',s)
    if not target_total and re.search(r'\b(?:budget|total|amount)\b',s) and not pos_before:
        target_total=re.search(r'\b(?:adjust|decrease|reduce|lower|cut|change|update|set|make)\s+(?:the\s+)?(?:amount\s+and\s+)?(?:decrease|reduce|set|change)?\s*(?:it\s+)?(?:to|at)\s*'+NUMBER+r'\b',s)
    if target_total:
        value,currency=amount_from(target_total)
        if value is not None:return {'type':'update_plan_budget','amount':value,'currency':currency}
    # An explicit total-budget delta is distinct from a per-campaign increase.
    total_delta=re.search(r'\b(?P<verb>increase|raise|decrease|reduce)\s+(?:(?:my|the|current|giving|plan|donation)\s+)*(?:total|budget|total\s+budget)\s+(?:by|with)\s*'+NUMBER+r'\b',s)
    if total_delta:
        val,cur=amount_from(total_delta)
        if val is not None:return {'type':'adjust_plan_budget','delta': val if total_delta.group('verb') in {'increase','raise'} else -val, 'currency':cur}
    # Unlike 'add 100 to campaign', here an amount changes the TOTAL.
    total=re.search(r'\b(?:change|update|set|make)\s+(?:(?:my|the|current|donation|giving|plan|total)\s+)*(?:budget|amount|total)\s+(?:to|at|as|=)?\s*'+NUMBER+r'\b',s)
    if total:
        val,cur=amount_from(total)
        if val is not None:return {'type':'update_plan_budget','amount':val,'currency':cur}
    return None

def validate_target(action: dict[str,Any], plan: Any) -> str|None:
    """Clarification messages, never an 'action succeeded' claim."""
    entries=getattr(plan,'items',[]) if plan else []
    typ=action.get('type','')
    if typ in {'update_plan_allocation','adjust_plan_allocation','remove_plan_item'}:
        if not entries:
            return 'There is no selected campaign in your current giving plan. Please choose a campaign first.'
        index=action['position']
        if index == -1:index=len(entries)
        if index<1 or index>len(entries):
            return f'Your current giving plan has {len(entries)} campaigns. Please choose one of those.'
        action['position']=index
    if typ in {'update_plan_allocation','adjust_plan_allocation'}:
        currency=action.get('currency','CURRENT')
        if plan and currency not in {'CURRENT',plan.currency}:
            return f'Your current plan uses {plan.currency}, but you specified {currency}. Please confirm a matching currency.'
        if typ=='adjust_plan_allocation':
            target=entries[action['position']-1]
            proposed=target.amount+action['delta']
            if proposed<1:
                return 'That change would leave the campaign with less than the minimum allocation. Please choose a smaller reduction.'
            # The frontend presents explicit choices if this delta exceeds the draft budget.
            # Do not silently charge, increase the budget, or reduce other allocations.
            action['campaign_id']=target.id
        if typ=='update_plan_allocation':action['campaign_id']=entries[action['position']-1].id
    if typ=='remove_plan_item' and entries:action['campaign_id']=entries[action['position']-1].id
    if typ in {'rebalance_plan','distribute_remaining'} and not entries:
        return 'Select campaigns in your giving plan first, then I can distribute the budget.'
    return None
