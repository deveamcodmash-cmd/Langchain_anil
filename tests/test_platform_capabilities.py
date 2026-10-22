"""Offline platform-wide capability/ACL and API contract tests."""
import hashlib
import hmac
import json
import os
import time
import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.capabilities import CATALOGUE, SUPPORTED_ROLES, list_capabilities, policy_decision
from app.intent_guard import assess
from app.knowledge import knowledge_prompt, matching_facts

client=TestClient(app)
SECRET='another-testing-secret-with-at-least-thirty-two-characters'


def signed_post(endpoint, payload):
    os.environ['FILANTROPHY_SHARED_SECRET']=SECRET
    raw=json.dumps(payload,separators=(',',':')).encode()
    stamp=str(int(time.time()))
    nonce=uuid.uuid4().hex
    digest=hmac.new(SECRET.encode(),stamp.encode()+b'.'+nonce.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return client.post(endpoint,content=raw,headers={
        'X-Filantrophy-Timestamp':stamp,
        'X-Filantrophy-Nonce':nonce,
        'X-Filantrophy-Signature':'sha256='+digest
    })


def test_unique_capability_keys():
    assert len({item.key for item in CATALOGUE}) == len(CATALOGUE)
    assert len(CATALOGUE) >= 18


def test_supported_roles():
    assert {'guest','individual','corporate','volunteer','event_organiser','service_provider','admin'} == SUPPORTED_ROLES


def test_all_planned_integrations_do_not_claim_executable():
    result = list_capabilities('admin')
    assert all(item['executable_by_python'] is False for item in result)
    assert all(item['status']=='planned' for item in result if item['area']=='events')


def test_admin_only_capability_denied_to_guest():
    assert policy_decision('admin.operations','guest')['reason']=='role_not_eligible'
    assert policy_decision('admin.operations','individual')['allowed'] is False


def test_admin_cannot_skip_authoritative_backend():
    assert policy_decision('admin.operations','admin',consent=True)['reason']=='integration_not_available'
    assert policy_decision('giving.single_checkout','individual',consent=True)['reason']=='authoritative_backend_required'


def test_no_charge_without_approval():
    assert policy_decision('giving.single_checkout','individual',consent=False)['reason']=='approval_required'


def test_public_search_usable_but_read_only():
    result=policy_decision('campaign.search','guest')
    assert result['allowed'] is True
    assert result['backend_authorization_required'] is True


def test_unknown_capability_denied():
    assert policy_decision('secret.export','admin')['allowed'] is False


def test_knowledge_payment_prompt_not_outdated():
    ctx=knowledge_prompt('What happens when my card payment succeeds?')
    assert 'Paystack' not in ctx
    assert 'server verifies' not in ctx.lower() or 'backend' in ctx.lower()
    assert 'backend' in ctx.lower()


def test_knowledge_does_not_invent_service_tool():
    ctx=knowledge_prompt('Can the AI book a service?')
    assert 'booking flow' in ctx.lower()
    assert 'genuine confirmation' in ctx.lower()
    assert 'not yet supported' in ctx.lower()


def test_knowledge_no_fake_policy():
    assert 'No verified answer-specific' in knowledge_prompt('What is the cancellation penalty?')


def test_scope_expanded():
    queries=['Find volunteer opportunities', 'Where are my event registrations?',
             'Help me book a service appointment', 'Show my corporate giving',
             'How do I see my followers?', 'Check my donation receipt']
    assert all(assess(query)=='in_scope' for query in queries)


def test_off_topic_code_even_with_platform_name():
    assert assess('<?php $config["stripe"]=1; make Filantrophy code better')=='off_topic'


def test_signed_capabilities_read_only():
    response=signed_post('/v1/capabilities',{'actor_role':'individual','area':'giving'})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['actor_role']=='individual'
    assert len(data['capabilities'])>=4
    assert all(i['area']=='giving' for i in data['capabilities'])
    assert all(i['executable_by_python'] is False for i in data['capabilities'])


def test_capabilities_requires_hmac():
    assert client.post('/v1/capabilities',json={'actor_role':'admin'}).status_code==401


def test_capabilities_reject_injected_role():
    response=signed_post('/v1/capabilities',{'actor_role':'superuser'})
    assert response.status_code==422


def test_policy_preview_cannot_authorize_admin_mutation():
    result=signed_post('/v1/policy-check',{'actor_role':'admin','capability_key':'admin.operations','explicit_approval':True})
    assert result.status_code==200
    assert result.json()['allowed'] is False


def test_policy_preview_guest_denied_private_history():
    result=signed_post('/v1/policy-check',{'actor_role':'guest','capability_key':'giving.history'})
    assert result.status_code==200
    assert result.json()['reason']=='role_not_eligible'


def test_excessive_payload_rejected():
    assert signed_post('/v1/capabilities', {'actor_role':'guest','nonsense':'X'*9000}).status_code==413


def test_knowledge_sources_have_identifiers():
    for query in ('donation plan', 'payment card', 'event booking', 'private account'):
        assert all(item['source'].startswith('filantrophy:') for item in matching_facts(query))


def test_future_mutations_never_claim_success():
    from app.future_actions import unsupported_action_reply
    from app.graph import run_workflow
    from app.schemas import ChatRequest
    for prompt in [
        'Register me for that event',
        'Apply for the volunteering opportunity',
        'Publish the campaign',
    ]:
        assert unsupported_action_reply(prompt)
        response=run_workflow(ChatRequest(message=prompt))
        assert response.mode=='integration_not_available'
        assert response.plan_proposal is None
        assert response.action_proposal is None
        assert response.agents_run==['Capability Guard']


def test_plan_update_contract_requires_exact_totals():
    from app.tool_contracts import PlanUpdateArgs
    from pydantic import ValidationError
    valid = dict(plan_id=45,expected_version=2,action_id='REQ_1234567890123456',
                 currency='NGN',amount_minor=300000,allocations=[
                     {'campaign_id':1,'amount_minor':100000},
                     {'campaign_id':2,'amount_minor':200000}
                 ])
    assert PlanUpdateArgs.model_validate(valid).amount_minor==300000
    bad={**valid,'amount_minor':200000}
    try:
        PlanUpdateArgs.model_validate(bad)
        assert False, 'Expected validation failure'
    except ValidationError: pass


def test_plan_update_contract_rejects_duplicate_ids():
    from app.tool_contracts import PlanUpdateArgs
    from pydantic import ValidationError
    try:
        PlanUpdateArgs(plan_id=45,expected_version=2,action_id='REQ_1234567890123456',
                       currency='NGN',amount_minor=200000,allocations=[
                           {'campaign_id':1,'amount_minor':100000},
                           {'campaign_id':1,'amount_minor':100000}
                       ])
        assert False, 'Expected duplicate rejection'
    except ValidationError: pass


def test_sensitive_data_blocked_before_model_call():
    from app.privacy_guard import contains_sensitive_payment_data
    from app.graph import run_workflow
    from app.schemas import ChatRequest
    for message in [
        'my card is 4242 4242 4242 4242',
        'api_key=abc123def456ghi789jk',
        'my key is sk-proj-'+'A'*36,
    ]:
        assert contains_sensitive_payment_data(message)
        result=run_workflow(ChatRequest(message=message))
        assert result.mode=='sensitive_data_blocked'
        assert result.plan_proposal is None
        assert '4242' not in result.reply
    assert contains_sensitive_payment_data('Donate ₦20,000') is False


def test_booking_requests_route_to_service_selection_not_fake_confirmation():
    from app.graph import run_workflow
    from app.schemas import ChatRequest, PlatformResource
    response=run_workflow(ChatRequest(message='Book a physiotherapy session',resources=[
        PlatformResource(id=85,title='Physiotherapy Session',kind='service',summary='Massage Therapy')
    ]))
    assert response.mode=='platform_search'
    assert [row.id for row in response.resources]==[85]
    assert 'confirmed' not in response.reply.lower()
