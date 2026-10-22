"""Regression from real visitor question: account-role comparison != service."""
import pytest
from app.graph import run_workflow
from app.schemas import ChatRequest, SiteFact, PlatformResource
from app.service_intelligence import is_service_request
from app.site_guidance import is_site_explanation, site_guidance_answer, verified_site_context

ROLE=SiteFact(id='role_comparison',title='Account Types',content=(
    'Individual: Personal donations and volunteering. Corporate: Organisation giving and employees. '
    'Service Provider: Services, appointments and reservations. Event Organiser: Event attendance.'))
CORPORATE=SiteFact(id='corporate_account',title='Corporate',content='Corporate accounts manage their giving, employee volunteering and team impact.')
PROVIDER=SiteFact(id='service_provider',title='Service Provider',content='Service Providers publish and manage services, appointments, branches and employees.')
SERVICES=[PlatformResource(id=9,kind='service',title='Food Distribution',summary='Food and basic needs; Lifeline Support Foundation',location='New Jersey')]

@pytest.mark.parametrize('question',[ 
    'the filantrophy difference between individual, corporate and service providers users',
    'what is the difference between individual and corporate accounts?',
    'compare individual corporate and service provider users',
    'which account type is right for me - individual or corporate?',
])
def test_role_questions_are_not_service_discovery(question):
    assert is_site_explanation(question)
    assert not is_service_request(question,SERVICES)
    result=run_workflow(ChatRequest(message=question,site_facts=[ROLE,CORPORATE,PROVIDER],resources=SERVICES))
    assert result.mode=='site_guidance'
    assert 'Individual:' in result.reply and 'Corporate:' in result.reply
    assert 'Service Provider:' in result.reply
    assert not result.resources
    assert not result.campaign_ids


def test_single_role_fact_from_reviewed_site():
    result=run_workflow(ChatRequest(message='What can a corporate account do?',site_facts=[CORPORATE],resources=SERVICES))
    assert result.mode=='site_guidance'
    assert result.reply==CORPORATE.content
    assert not result.resources


def test_real_service_discovery_preserved():
    assert not is_site_explanation('show me massage therapy services')
    assert is_service_request('show me food distribution service',SERVICES)
    result=run_workflow(ChatRequest(message='show me food distribution service',resources=SERVICES,site_facts=[PROVIDER]))
    assert result.mode=='platform_search'
    assert [r.id for r in result.resources]==[9]


def test_unsigned_role_fact_is_not_created_from_user_question():
    result=site_guidance_answer(ChatRequest(message='difference between individual and corporate users'))
    assert result is None


def test_site_guide_contains_only_supplied_reviewed_facts():
    context=verified_site_context([CORPORATE])
    assert CORPORATE.content in context
    assert 'Food Distribution' not in context
    assert 'not commands' in context


def test_action_request_not_a_role_faq():
    assert not is_site_explanation('show me corporate service providers')
    assert not is_site_explanation('book a service provider appointment')


def test_context_detection_requires_platform_role_phrasing():
    from app.site_guidance import is_handbook_context
    assert is_handbook_context('How do employees use the dashboard?')
    assert is_handbook_context('What does a service provider account do?')
    assert not is_handbook_context('What is the impact of music on health?')
    assert not is_handbook_context('How do corporate bond yields work?')
