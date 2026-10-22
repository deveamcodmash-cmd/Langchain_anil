"""Model-led intent normalization and evidence boundaries.

The LLM interprets language; this module enforces which capabilities have
verified backing. No raw chat text authorizes checkout, booking, or mutations.
"""
from __future__ import annotations

from typing import Any

INFORMATION_INTENTS = frozenset({
    'donation_explanation', 'current_world_information',
    'popularity_comparison', 'platform_explanation', 'general_knowledge', 'social_impact_context',
})


def normalize_decision(raw: dict[str, Any]) -> dict[str, Any]:
    """Resolve model intent/route disagreement without keyword overfitting.

    Legacy fake routers may supply only ``route``; keep those tests compatible.
    """
    decision = dict(raw)
    intent = str(decision.get('intent') or 'unspecified')
    if intent in INFORMATION_INTENTS:
        decision['route'] = 'knowledge'
    elif intent == 'campaign_discovery':
        decision['route'] = 'discovery'
    elif intent == 'giving_plan':
        decision['route'] = 'plan'
    elif intent == 'unrelated':
        decision['route'] = 'knowledge'
    else:
        decision['route'] = decision.get('route') if decision.get('route') in {'discovery','knowledge','plan','out_of_scope'} else 'knowledge'
    return decision


def evidence_notice(intent: str) -> str:
    """Factual limits never depend on model optimism."""
    if intent == 'current_world_information':
        return ('There is no verified live disaster-news feed in this request. '
                'Do not list incidents as current, recent or active. Explain that current events cannot be confirmed here; '
                'offer to look at published Filantrophy disaster-relief campaigns instead. ')
    if intent == 'popularity_comparison':
        return ('There are no verified donation velocity, popularity ranking or trending metrics in this request. '
                'Do not call a campaign trending, most donated to, hot or urgent without verified evidence. '
                'If appropriate, offer published campaigns, or ask whether the user means urgent causes or popular donations. ')
    if intent == 'donation_explanation':
        return ('A donation amount may mean the amount the user wishes to give, the campaign goal, '
                'or funds raised. Distinguish them. Do not invent minimums, processing fees or account balances. ')
    return ''


def search_failure_guidance(intent: str, has_catalogue: bool) -> str:
    source = ('The connected eligible published campaign snapshot has no matching records.'
              if has_catalogue else 'The supplied eligible published campaign snapshot is empty.')
    return (source + ' Do not say the entire Filantrophy platform has no such campaigns. '
            'Do not invent campaign titles, links, images, availability or factual disaster news. '
            'Respond to the actual user intent in 1–2 natural sentences; offer a useful next step backed by the supplied catalogue, '
            'or ask only one clarifying question. Other available categories are NOT direct matches. '
            'Never say that a missing cause is coming soon without an approved roadmap. Avoid generic repeated failure sentences. '
            + evidence_notice(intent))


def compact_history(history: list[dict[str, Any]], limit: int = 12) -> list[dict[str, str]]:
    """Retain user context, de-duplicate identical assistant failure messages.

    The original account conversation is unchanged; this is only the bounded
    model input. Past assistant claims never become authoritative facts.
    """
    from .conversation_context import recent_conversation
    turns = recent_conversation(history, min(20, max(1, limit)))
    seen_assistant = set()
    result = []
    for turn in reversed(turns):
        if turn['role'] == 'assistant':
            content = turn['content'].casefold().strip()
            if content in seen_assistant:
                continue
            seen_assistant.add(content)
        result.append(turn)
    return list(reversed(result))


def is_repeated_reply(reply: str, history: list[dict[str, Any]]) -> bool:
    """Detect identical/near-identical assistant loops without inspecting private data."""
    from difflib import SequenceMatcher
    current = ' '.join(reply.casefold().split())[:700]
    if not current:
        return False
    for item in history[-12:]:
        if item.get('role') != 'assistant':
            continue
        previous = ' '.join(str(item.get('content', '')).casefold().split())[:700]
        if previous and SequenceMatcher(None, current, previous).ratio() >= .88:
            return True
    return False
