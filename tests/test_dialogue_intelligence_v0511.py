"""Real screenshots → expected non-mutating routing and grounding contracts."""
from __future__ import annotations
import pytest
from app.dialogue_intelligence import resolve_offer, booking_help, general_only_question, platform_guidance, off_topic_reminder
from app.graph import run_workflow
from app.schemas import ChatRequest, Campaign, ConversationMessage, PlatformResource, BookingContext
from app.service_intelligence import is_service_request

ANIMAL = [Campaign(id=12, title='Save Abandoned Pets',category='Animal Welfare',tags=['rescue'],currency='USD')]
UNRELATED = [Campaign(id=33,title='School Meals',category='Education',currency='USD')]
SERVICE = [PlatformResource(id=9,title='Yoga & Meditation Session',kind='service',location='Chandigarh'),
           PlatformResource(id=8,title='Education Assistance Program',kind='service',location='New Delhi')]

def history(*values):
    return [ConversationMessage(role=role,content=text) for role,text in values]

@pytest.mark.parametrize('msg',[
    'recommend me best sex movie list','provide me sex movies list','recommend me sex positions',
    'recommend dog breeding techniques','who is taylor swift','Tell me a joke',
])
def test_general_questions_never_call_service_directory(msg):
    assert general_only_question(msg)
    assert not is_service_request(msg,SERVICE)

@pytest.mark.parametrize('msg', ['guide me booking form','guide me Yoga & Meditation Session form','how do I fill the booking form'])
def test_guidance_is_not_search(msg):
    assert not is_service_request(msg,SERVICE)
    r=run_workflow(ChatRequest(message=msg,resources=SERVICE,booking_context=BookingContext(active=True,service_id=9,stage='date')))
    assert r.mode=='booking_guidance' and 'Yoga & Meditation Session' in r.reply and not r.resources
    assert 'date' in r.reply.lower()


def test_followup_yes_executes_last_offer():
    r=run_workflow(ChatRequest(message='yes',campaigns=ANIMAL+UNRELATED,history=history(
        ('user','recommend dog breeding techniques'),
        ('assistant','Would you like me to show animal welfare campaigns?'))))
    assert r.mode=='followup_resolved'
    assert r.campaign_ids==[12] and r.catalogue_result_ids==[12]


def test_followup_elliptical_offer_uses_recent_topic():
    r=run_workflow(ChatRequest(message='yes',campaigns=ANIMAL+UNRELATED,history=history(
        ('user','find animal welfare campaigns'),
        ('assistant','Would you like me to show some of those campaigns?'))))
    assert r.campaign_ids==[12]


def test_empty_followup_stops_loop_no_fake_candidates():
    r=run_workflow(ChatRequest(message='yes',campaigns=UNRELATED,history=history(
        ('user','recommend dog breeding techniques'),
        ('assistant','Would you like me to show animal welfare campaigns?'))))
    assert r.mode=='followup_resolved' and r.campaign_ids==[]
    assert 'did not find' in r.reply and 'would you like me' not in r.reply.lower()


def test_yes_does_not_infer_old_offer_after_new_user_message():
    r=resolve_offer(ChatRequest(message='yes',campaigns=ANIMAL,history=history(
        ('assistant','Would you like me to show animal campaigns?'),
        ('user','actually tell me about music'))))
    assert r is None


def test_booking_context_must_match_server_catalogue():
    r=booking_help(ChatRequest(message='guide me booking form',resources=SERVICE,
           booking_context=BookingContext(active=True,service_id=129,stage='review')))
    assert r.mode=='booking_guidance' and 'Yoga' not in r.reply
    assert 'payment' not in r.reply.lower() or 'confirm' in r.reply.lower()


def test_booking_guidance_never_submits_or_charges():
    r=run_workflow(ChatRequest(message='guide me booking form',resources=SERVICE,
        booking_context=BookingContext(active=True,service_id=9,stage='review')))
    assert r.action_proposal is None and r.plan_proposal is None
    assert 'not submitted' in r.reply


def test_campaign_creation_uses_reviewed_workflow():
    r=run_workflow(ChatRequest(message='how to create a campaign'))
    assert r.mode=='platform_guidance'
    for word in ['beneficiary','currency','cover image','milestones']:
        assert word in r.reply.lower()


def test_top_charity_requires_comparable_raising_data():
    missing=run_workflow(ChatRequest(message='let me top charity',campaigns=UNRELATED))
    assert missing.mode=='ranking_unavailable'
    verified=[Campaign(id=1,title='A',public_progress=True,raised=400,currency='USD'),
              Campaign(id=2,title='B',public_progress=True,raised=700,currency='NGN'),
              Campaign(id=3,title='C',public_progress=True,raised=600,currency='USD')]
    out=run_workflow(ChatRequest(message='show top charity',campaigns=verified))
    assert out.mode=='verified_ranking' and set(out.campaign_ids)=={2,3}
    assert 'all-platform' in out.reply and 'USD 600' in out.reply


def test_time_available_without_model():
    r=run_workflow(ChatRequest(message='what is time now'))
    assert r.mode=='general_knowledge' and 'UTC' in r.reply


def test_brand_pivot_once_not_on_every_message():
    first=ChatRequest(message='recommend dog breeding techniques')
    reply=off_topic_reminder(first,'Good breeding requires veterinary checks.')
    assert reply.count('Filantrophy')==1
    next_turn=ChatRequest(message='best sex movies list',history=history(
        ('user',first.message),('assistant',reply)))
    assert 'I can also help with Filantrophy' not in off_topic_reminder(next_turn,'Here is an overview.')


def test_platform_request_not_recast_as_general_knowledge():
    assert not general_only_question('Find animal welfare campaigns on Filantrophy')
    assert is_service_request('show me yoga sessions', SERVICE)


def test_declined_offer_does_not_repeat_question():
    r=run_workflow(ChatRequest(message='no thanks',history=history(
        ('assistant','Would you like me to show animal welfare campaigns?'))))
    assert r.mode=='followup_resolved' and 'would you like' not in r.reply.lower()
    assert not r.campaign_ids and not r.resources
