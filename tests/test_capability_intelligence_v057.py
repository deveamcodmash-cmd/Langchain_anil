"""Regression cases from Filantrophy visitor screenshots. No live database or LLM."""
from app.schemas import ChatRequest
from app.graph import run_workflow
from app.account_queries import capability


def request(text, **kwargs):
    return ChatRequest(message=text, **kwargs)


def test_upcoming_booking_is_not_catalogue_search():
    r=run_workflow(request('do you remember my booking any upcomings',resources=[
        {'id':1,'title':'Physiotherapy','kind':'service'}],account_context={
        'signed_in':True,'bookings_available':True,'upcoming_bookings':[
            {'booking_id':10,'service_title':'Physiotherapy', 'booking_date':'2026-11-01','start_label':'9:00 AM','status_label':'Confirmed'}]
    }))
    assert r.mode=='account_read'
    assert 'Physiotherapy' in r.reply and 'November' not in r.reply
    assert '2026-11-01' in r.reply
    assert r.agents_run==['Authenticated Bookings']


def test_signed_out_account_does_not_expose_any_bookings():
    r=run_workflow(request('Show my upcoming bookings',account_context={'signed_in':False}))
    assert r.mode=='signin_required'
    assert 'Sign in' in r.reply


def test_unconnected_booking_table_is_not_misreported_as_zero_bookings():
    r=run_workflow(request('when is my next appointment',account_context={'signed_in':True,'bookings_available':False}))
    assert r.mode=='account_read'
    assert 'My Bookings' in r.reply
    assert 'no upcoming appointments' not in r.reply.casefold()


def test_no_upcoming_bookings_is_only_stated_after_verified_lookup():
    r=run_workflow(request('show my upcoming appointments',account_context={'signed_in':True,'bookings_available':True}))
    assert 'no upcoming appointments' in r.reply.lower()


def test_my_giving_uses_completed_donation_aggregates_not_memory():
    r=run_workflow(request("to which cause i'm donating more",account_context={
        'signed_in':True,'donations_available':True,'donation_totals':[
            {'campaign_id':1,'campaign_title':'Water Relief','currency':'USD','amount':60},
            {'campaign_id':2,'campaign_title':'Food Bank','currency':'USD','amount':100},
        ]}))
    assert r.mode=='account_read'
    assert 'Food Bank' in r.reply
    assert 'USD 100.00' in r.reply


def test_cross_currency_my_donations_are_not_added_or_ranked_together():
    r=run_workflow(request('where have I donated the most?',account_context={
        'signed_in':True,'donations_available':True,'donation_totals':[
            {'campaign_id':1,'campaign_title':'Flood Aid','currency':'USD','amount':60},
            {'campaign_id':2,'campaign_title':'Food Bank','currency':'NGN','amount':100000},
        ]}))
    assert 'by currency' in r.reply and 'USD 60.00' in r.reply and 'NGN 100,000.00' in r.reply


def test_missing_donation_status_does_not_claim_no_donations():
    r=run_workflow(request('which cause have I donated most to',account_context={'signed_in':True}))
    assert r.mode=='account_data_unavailable'
    assert 'no completed donations' not in r.reply.lower()


def test_public_campaign_ranking_uses_verified_public_progress():
    r=run_workflow(request('who this current highest raised campaign',campaigns=[
        {'id':1,'title':'School Supplies','currency':'USD','raised':1200,'public_progress':True},
        {'id':2,'title':'Water Relief','currency':'USD','raised':1550,'public_progress':True},
        {'id':3,'title':'Private Campaign','currency':'USD','raised':999999,'public_progress':False},
    ]))
    assert r.mode=='verified_ranking'
    assert r.campaign_ids==[2]
    assert 'Water Relief' in r.reply and 'Private Campaign' not in r.reply
    assert 'available listings' in r.reply


def test_public_campaign_currency_division():
    r=run_workflow(request('which campaign raised the most money',campaigns=[
        {'id':1,'title':'US Relief','currency':'USD','raised':100,'public_progress':True},
        {'id':2,'title':'Nigeria Relief','currency':'NGN','raised':100000,'public_progress':True},
    ]))
    assert set(r.campaign_ids)=={1,2}
    assert 'different currencies' in r.reply


def test_public_campaign_no_raise_info_cannot_invent_leader():
    r=run_workflow(request('highest raised campaign',campaigns=[{'id':1,'title':'School','currency':'USD'}]))
    assert r.mode=='ranking_unavailable'
    assert 'do not include comparable' in r.reply


def test_latest_services_sorted_only_by_real_publication_dates():
    r=run_workflow(request('what is latest service',resources=[
        {'id':1,'title':'Yoga','kind':'service','published_at':'2026-09-01 00:00:00'},
        {'id':2,'title':'Therapy','kind':'service','published_at':'2026-10-01 00:00:00'},
    ]))
    assert [s.id for s in r.resources]==[2,1]
    assert r.mode=='platform_search'


def test_latest_service_missing_dates_has_no_fake_newest_claim():
    r=run_workflow(request('what is latest service',resources=[{'id':1,'title':'Yoga','kind':'service'}]))
    assert r.resources and 'not included' in r.reply


def test_sensitive_general_questions_are_not_intercepted_by_search():
    assert capability('what is the current best sex toys') is None
    assert capability('is there any services with sex') is None
    assert capability('what is wrong in our environment') is None
    assert capability('what is currently wrong in our society and which campaigns help?') is None


def test_not_all_booking_mentions_are_private_lookup():
    assert capability('book a physiotherapy appointment') is None
    assert capability('show service providers for yoga') is None


def test_signed_account_fields_cannot_be_guessed_from_user_text():
    r=run_workflow(request('show my bookings from user 12345',account_context={'signed_in':False}))
    assert r.mode=='signin_required'


def test_ambiguous_service_subject_gets_neutral_clarification():
    r=run_workflow(request('is there any services with sex'))
    assert r.mode=='platform_search'
    assert not r.resources
    assert 'sexual-health' in r.reply
    assert 'matching service' not in r.reply


def test_educational_service_question_skips_catalogue_interception():
    from app.platform_search import resource_search
    assert resource_search(request('what is a sexual health clinic',resources=[
        {'id':25,'title':'Wellness Clinic','kind':'service'}])) is None
