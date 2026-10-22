"""New response intelligence regression coverage; no remote LLM dependency."""
import pytest

from app.conversation_voice import (
    VOICE_POLICY, tone_flags, eligible_categories, related_categories,
    neutral_fallback, tone_rewrite_instruction,
)
from app.intelligence import normalize_decision


@pytest.mark.parametrize('reply,expected', [
    ('I do not have information on trending causes.', 'discouraging_opening'),
    ('You should already know this.', 'judgmental_wording'),
    ('That is stupid.', 'judgmental_wording'),
    ("I don't have verified rankings here.", 'discouraging_opening'),
    ('None of the listed campaigns end this week.', 'discouraging_opening'),
    ('I could not find a matching eligible published campaign.', 'stock_search_failure'),
    ('Try a different cause or location.', 'stock_search_failure'),
    ('Explore the current public campaigns. Would you like me to?', 'generic_closing'),
    ('Disaster relief support is Coming Soon!', 'unapproved_roadmap_promise'),
    ('This service will launch soon!', 'unapproved_roadmap_promise'),
])
def test_poor_style_and_unverified_roadmap_are_flagged(reply, expected):
    assert expected in tone_flags(reply)


@pytest.mark.parametrize('reply', [
    'You can choose your contribution amount and review it before checkout.',
    'For timely details, check a reliable current source. I can also help explore published relief campaigns.',
    'Madagascar is an island country off southeastern Africa.',
    'The public fundraising progress shows $120 raised toward a $500 goal.',
    'This search did not return a match. We can try another region.',
    'Corruption can affect the delivery of public services, and accountability matters.',
])
def test_helpful_truthful_replies_are_allowed(reply):
    assert tone_flags(reply) == []


def test_category_alternatives_use_only_verified_metadata():
    records = [
        {'category': 'Healthcare', 'title': 'Community Clinic'},
        {'category': 'Healthcare', 'title': 'Medical Supplies'},
        {'category': 'Relief', 'title': 'Winter Assistance'},
        {'category': 'Uncategorized', 'title': 'Miscellaneous'},
    ]
    assert eligible_categories(records) == ['Healthcare', 'Relief']
    assert eligible_categories([]) == []


def test_specific_missing_disaster_search_never_promotes_unrelated_arts():
    records = [{'title':'Art Fair','category':'Culture','summary':'Art gallery', 'tags':[]}]
    assert related_categories(records, 'I want to donate to disaster areas') == []
    reply = neutral_fallback('campaign_discovery', related_categories(records, 'I want to donate to disaster areas'))
    assert 'Culture' not in reply
    assert 'broaden' in reply


def test_verified_related_topic_may_be_suggested_as_alternative():
    records = [
        {'title':'Flood Response','category':'Community Relief','summary':'Flood assistance','tags':['Emergency','Flood']},
        {'title':'Art Fair','category':'Culture','summary':'Gallery','tags':[]},
    ]
    assert related_categories(records, 'Find flood assistance') == ['Community Relief']
    assert 'Community Relief' in neutral_fallback('campaign_discovery', ['Community Relief'])


@pytest.mark.parametrize('intent', ['general_knowledge','social_impact_context'])
def test_general_and_social_impact_questions_use_knowledge_not_campaign_search(intent):
    assert normalize_decision({'intent':intent,'route':'discovery'})['route']=='knowledge'


def test_world_news_limitation_is_courteous_and_grounded():
    text = neutral_fallback('current_world_information')
    assert 'reliable news source' in text
    assert 'today' not in text.lower()
    assert not tone_flags(text)


def test_no_verified_trending_rank_is_invented():
    text = neutral_fallback('popularity_comparison')
    assert 'different from a verified live popularity ranking' in text
    assert not tone_flags(text)


def test_voice_policy_preserves_significant_safety_qualifications():
    assert 'do not obscure material risks' in VOICE_POLICY.lower()
    assert 'approved' in VOICE_POLICY.lower()
    assert 'never add campaign names' in tone_rewrite_instruction().lower()


def test_trusted_alternatives_not_coming_soon():
    text = neutral_fallback('campaign_discovery', ['Education', 'Healthcare'])
    assert 'Education' in text and 'Healthcare' in text
    assert 'Coming Soon' not in text
