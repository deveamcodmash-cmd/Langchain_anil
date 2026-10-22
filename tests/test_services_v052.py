"""Reported user screenshots: precise service search, never campaign fallback."""
from app.graph import run_workflow
from app.platform_search import resource_search
from app.schemas import ChatRequest, PlatformResource

SERVICES=[
    PlatformResource(id=85,title='Physiotherapy Session',kind='service',summary='MASSAGE THERAPY · Serenity Wellness Centre · Personalized therapy to improve movement and mobility.',location='Wellness & Holistic Health'),
    PlatformResource(id=86,title='Yoga & Meditation Session',kind='service',summary='Yoga & Meditation · Serenity Wellness Centre',location='Abuja, Nigeria'),
    PlatformResource(id=87,title='Dental Checkup',kind='service',summary='Dental Care',location='Osun, Nigeria'),
]

def search(message):
    return run_workflow(ChatRequest(message=message,resources=SERVICES,campaigns=[
        {'id':11,'title':'Healthcare Fundraiser','currency':'USD','summary':'Healthcare services for children'}
    ]))


def test_physio_title_without_word_service():
    result=search('show me Physiotherapy Session')
    assert result.mode=='platform_search'
    assert [s.id for s in result.resources]==[85]
    assert not result.campaign_ids


def test_physio_title_noun_phrase():
    result=search('Physiotherapy Session service')
    assert [s.id for s in result.resources]==[85]


def test_massage_category_bare_phrase():
    result=search('massage therapy')
    assert [s.id for s in result.resources]==[85]


def test_massage_category_conversational():
    result=search('show me services related to massage therapy')
    assert [s.id for s in result.resources]==[85]


def test_missing_service_does_not_substitute_campaign():
    result=search('show me reiki services')
    assert result.mode=='platform_search'
    assert not result.resources
    assert not result.campaign_ids


def test_explicit_campaign_keeps_campaign_intent():
    assert resource_search(ChatRequest(message='show me healthcare campaigns with physiotherapy',resources=SERVICES)) is None


def test_generic_service_results_are_public_catalogue():
    result=search('show me services')
    assert [s.id for s in result.resources]==[85,86,87]


def test_named_service_booking_returns_card_not_fake_confirmation():
    result=search('Book a physiotherapy session')
    assert [s.id for s in result.resources]==[85]
    assert 'confirmed' not in result.reply.casefold()


def test_campaign_health_without_service_word_not_hijacked():
    assert resource_search(ChatRequest(message='Show me Healthcare Campaigns',resources=SERVICES)) is None


def test_exact_requested_count():
    result=search('Show me one service')
    assert len(result.resources)==1


def test_location_filter_never_returns_different_city():
    result=search('Find yoga services in Abuja')
    assert [s.id for s in result.resources]==[86]
    result=search('Find yoga services in Lagos')
    assert not result.resources


def test_generic_service_search_with_city():
    result=search('Show me services in Abuja')
    assert [s.id for s in result.resources]==[86]


def test_show_more_cursor_contains_complete_ranked_services():
    many=[PlatformResource(id=i,title=f'Massage Therapy {i}',kind='service',summary='Massage') for i in range(1,15)]
    result=resource_search(ChatRequest(message='show me massage services',resources=many))
    assert len(result.resources)==10
    assert len(result.resource_result_ids)==14
    assert result.resource_result_ids[:10]==[r.id for r in result.resources]


def test_return_no_fake_bookings_or_prices():
    result=search('Book physiotherapy session')
    assert result.resources
    assert 'booked' not in result.reply.casefold() and 'payment successful' not in result.reply.casefold()
