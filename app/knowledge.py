"""Versioned, deliberately narrow, reviewed platform knowledge.

This is a starter knowledge layer, not a claim that all future workflows work.
User-supplied messages/campaign descriptions are never added here.
"""
from __future__ import annotations
import re

# Each entry comes from the existing integration's verified behaviour or an
# explicit implementation limitation; no generated website policies.
FACTS = (
    ('assistant_capabilities', ('capabilities', 'features', 'abilities', 'help', 'can you'),
     'The assistant can help discover eligible published campaigns and some connected service, event and volunteering listings; prepare editable giving plans; and propose safe changes to a giving-plan draft. Service booking uses a separate user-confirmed booking flow. The assistant cannot independently verify payments or register someone for an event.'),
    ('brand', ('filantrophy', 'brand', 'name'),
     'Filantrophy is the official platform name. Use that exact spelling. Keep internal software and payment-provider names out of public responses.'),
    ('campaigns', ('campaign', 'causes', 'education', 'healthcare', 'fundraiser', 'find'),
     'The assistant currently discovers published campaigns from a catalogue provided by Filantrophy. Results can be limited by that catalogue; do not claim all platform campaigns were searched.'),
    ('giving_plans', ('plan', 'budget', 'split', 'allocate', 'donation', 'give'),
     'Giving plans are editable proposals. Budget changes in chat modify the draft; authenticated users save the plan separately. Preparing a plan never charges a card.'),
    ('payments', ('pay', 'payment', 'checkout', 'charge', 'card', 'fee'),
     'The Filantrophy website handles embedded card checkout after explicit user approval. Fees must be shown before confirmation. The trusted backend confirms payment and records campaign allocations. Never claim payment succeeded based on an AI answer.'),
    ('payment_support', ('failed', 'refund', 'pending', 'receipt', 'dispute'),
     'For payment questions, rely on verified platform transaction status. If status is unavailable, direct the user to their giving activity or official support. Never promise a refund or receipt without a record.'),
    ('other_services', ('volunteer', 'event', 'booking', 'service', 'corporate', 'organiser', 'provider'),
     'Filantrophy includes volunteering, events, corporate giving and service-provider experiences. The assistant can search connected published listings and open the site\'s existing service-booking flow. A service booking is confirmed only after the customer approves it and the verified platform backend returns a genuine confirmation. Event registration, volunteer applications and provider administrative mutations are not yet supported as AI actions.'),
    ('privacy', ('account', 'private', 'profile', 'history', 'personal'),
     'Personal records can only be accessed through authenticated, authorised platform APIs. Do not reveal one user\'s details to another.'),
)


def matching_facts(query: str, max_facts: int = 4) -> list[dict]:
    tokens=set(re.findall(r'[a-z]+',query.lower()))
    scored=[]
    for key,keywords,content in FACTS:
        score=sum(1 for keyword in keywords if keyword in tokens or (len(keyword)>4 and keyword in query.lower()))
        if score:
            scored.append((score,key,content))
    scored.sort(key=lambda x:(-x[0],x[1]))
    return [{'source':f'filantrophy:{key}','content':content} for _,key,content in scored[:max_facts]]


def knowledge_prompt(query: str) -> str:
    facts=matching_facts(query)
    return '\n'.join(f"- [{f['source']}] {f['content']}" for f in facts) if facts else (
        'No verified answer-specific platform fact is available. Ask a concise clarification or '
        'say you cannot verify the policy or workflow; do not make up capabilities.'
    )
