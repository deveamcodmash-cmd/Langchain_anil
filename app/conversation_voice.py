"""Grounded, inclusive visitor-facing response policy.

Language generation is model-led; constraints on facts, credentials, capabilities,
permissions and transactions are deterministic and cannot be softened by tone.
"""
from __future__ import annotations

import re
from typing import Any

VOICE_POLICY = (
    'Speak as a courteous, thoughtful Filantrophy assistant. First address the actual question; '
    'then, only when helpful, give one concrete, relevant next step. Use everyday language and '
    'respectful, non-judgmental wording, especially for crises, poverty, health and corruption. '
    'Keep most replies to 1–3 concise sentences and ask at most one necessary question. '
    'Do not use flattery, moral judgments, artificial optimism, rehearsed greetings, repeated apologies, '
    'or a standard closing such as "Would you like that?" after every reply. '
    'When a specific campaign or capability is absent from the supplied results, describe the '
    'limit briefly and emphasize what the visitor CAN explore, using only the supplied verified options. '
    'Do not claim a matching campaign exists if none was found. Do not redirect unrelated factual '
    'questions into campaign discovery. If the user asks about a serious or difficult subject, '
    'do not obscure material risks or facts just to sound positive. '
    'NEVER say a campaign, feature, service or event is "coming soon", planned or launching '
    'unless the request includes an explicitly approved, verified roadmap status. '
    'It is acceptable to say that available options may change as campaigns are published, '
    'without promising that any particular cause or feature will arrive. '
    'No invented deadlines, current events, campaign availability, rankings, verified impact, '
    'transaction results, policy rules, prices or guarantees. '
)

# Signals for a *single* stylistic retry, not forbidden expressions: a truthful
# limitation is allowed and sometimes essential. These identify unhelpful openings.
POOR_OPENINGS = re.compile(
    r"^\s*(?:i\s+(?:do\s+not|don['’]t)\s+have\s+(?:information|data|verified)|"
    r"i\s+(?:cannot|can['’]t|could\s+not|couldn['’]t)\s+(?:find|verify|provide)\b|"
    r"none\s+of\s+the\s+(?:listed|available)\b|"
    r"there\s+(?:are|is)\s+no\s+(?:matching|verified|available)\b)",
    re.I,
)
STOCK_FAILURE = re.compile(r"matching eligible published campaign|try a different cause or location", re.I)
ROUTINE_CLOSING = re.compile(r"\bwould you like (?:me to|that|to see those)\?\s*$", re.I)
JUDGMENTAL_LANGUAGE = re.compile(
    r"\b(?:that(?:'s| is) (?:stupid|dumb)|you (?:clearly )?(?:do not|don't) understand|"
    r"you should (?:already )?know|your (?:ignorance|stupidity)|it's (?:all )?your fault)\b",
    re.I,
)
UNAPPROVED_PROMISE = re.compile(r"\bcoming soon\b|\b(?:will|is going to) (?:be )?(?:added|launch|arrive|be available)\s+soon\b", re.I)


def tone_flags(reply: str) -> list[str]:
    """Surface testable risk signals; not a sentiment or offensiveness classifier."""
    result: list[str] = []
    if not reply.strip():
        return ['empty']
    if POOR_OPENINGS.search(reply):
        result.append('discouraging_opening')
    if STOCK_FAILURE.search(reply):
        result.append('stock_search_failure')
    if JUDGMENTAL_LANGUAGE.search(reply):
        result.append('judgmental_wording')
    if ROUTINE_CLOSING.search(reply):
        result.append('generic_closing')
    if UNAPPROVED_PROMISE.search(reply):
        result.append('unapproved_roadmap_promise')
    return result


def eligible_categories(campaigns: list[dict[str, Any]], limit: int = 3) -> list[str]:
    """Grounded alternative categories from the *published, eligible* Joomla snapshot.

    Do not imply these are relevant matches or suggest titles/links we have not
    verified. A category's existence does not prove urgency or popularity.
    """
    output: list[str] = []
    seen: set[str] = set()
    for row in campaigns:
        category = re.sub(r'\s+', ' ', str(row.get('category') or '').strip())
        if not category or category.casefold() in {'campaign', 'other', 'general', 'uncategorized'}:
            continue
        if category.casefold() not in seen:
            output.append(category[:80])
            seen.add(category.casefold())
        if len(output) >= limit:
            break
    return output


def neutral_fallback(intent: str, categories: list[str] | None = None) -> str:
    """Safe recovery if a model call fails or twice returns unusable language."""
    options = [str(c) for c in (categories or [])[:3] if str(c).strip()]
    if intent == 'current_world_information':
        return ('For the latest developments, a current, reliable news source is the best reference. '
                'On Filantrophy, I can help you explore published relief campaigns where available.')
    if intent == 'popularity_comparison':
        return ('We can explore published campaigns and compare their publicly displayed progress. '
                'That is different from a verified live popularity ranking.')
    if intent == 'donation_explanation':
        return ('Your donation amount is the amount you choose to contribute. '
                'If you mean a campaign’s funding goal or amount raised, I can explain those figures too.')
    if intent == 'campaign_discovery':
        if options:
            # Display examples, not false substitutes for the requested topic.
            return ('This particular search did not return a published match. '
                    'Other causes currently listed include ' + ', '.join(options) + '; you can explore those while new campaigns are published.')
        return ('This particular search did not return a published match in the current results. '
                'We can broaden the cause or location to explore more options.')
    return 'I can help you explore the Filantrophy information available for this topic. Which part would be most useful?'


def tone_rewrite_instruction() -> str:
    return (
        'Revise the wording only; preserve the verified meaning. Answer the current user question first. '
        'Replace discouraging stock openings with an accurate, forward-looking answer and a concrete next step '
        'if one exists. Mention only approved factual options given in the input. '
        'Never add campaign names, current events, trending rankings, availability, fees, actions or roadmap promises. '
        'Preserve any material disclosure of missing verification or risk. Avoid generic closing questions. '
        'Reply in plain text, one to three sentences unless more detail is needed.'
    )

# Campaign categories can be presented as specific suggestions only when the
# actual query overlaps verified public campaign metadata. Otherwise, offering
# an unrelated topic as an "alternative" can feel insensitive.
QUERY_STOP_WORDS = frozenset(
    'i my me we the that this those these and or to for in at with from where what who which '
    'is are can would want like please a an donations donation donating donate giving campaigns campaign '
    'causes cause find search show list support currently current available near of on all platform'.split()
)


def related_categories(campaigns: list[dict[str, Any]], question: str, limit: int = 3) -> list[str]:
    terms = {word for word in re.findall(r'[a-z]{3,}', question.casefold()) if word not in QUERY_STOP_WORDS}
    if not terms:
        return []
    related: list[dict[str, Any]] = []
    for campaign in campaigns:
        text = ' '.join(str(campaign.get(key) or '') for key in ('title','category','summary','location'))
        text += ' ' + ' '.join(str(t) for t in (campaign.get('tags') or []))
        words = set(re.findall(r'[a-z]{3,}', text.casefold()))
        if terms.intersection(words):
            related.append(campaign)
    return eligible_categories(related, limit)
