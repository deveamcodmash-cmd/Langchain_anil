"""Regression scenarios for the real user screenshot and financial guardrails."""
import pytest
from app.schemas import CurrentPlan,CurrentPlanItem,ChatRequest,Campaign,PlatformResource
from app.graph import run_workflow
from app.plan_intelligence import classify_plan_command


def plan():
    return CurrentPlan(currency='USD',budget=10000,items=[
        CurrentPlanItem(id=34,amount=3334),CurrentPlanItem(id=23,amount=3333),
        CurrentPlanItem(id=46,amount=3333)])

@pytest.mark.parametrize('text,typ,position,delta',[
    ('in the second campaign that i going to donate add 100','adjust_plan_allocation',2,100),
    ('add 100 to second campaign','adjust_plan_allocation',2,100),
    ('increase the second campaign by 100','adjust_plan_allocation',2,100),
    ('reduce first campaign by 50','adjust_plan_allocation',1,-50),
    ('add 100 to the last one','adjust_plan_allocation',-1,100),
])
def test_relative_actions(text,typ,position,delta):
    parsed=classify_plan_command(text)
    assert parsed['type']==typ
    assert parsed['position']==position
    assert parsed['delta']==delta

def test_screenshot_current_plan_exact_id():
    r=run_workflow(ChatRequest(message='in the second campaign that i going to donate add 100', current_plan=plan()))
    assert r.mode=='action_proposed'
    assert r.action_proposal['type']=='adjust_plan_allocation'
    assert r.action_proposal['position']==2 and r.action_proposal['campaign_id']==23
    assert r.action_proposal['currency']=='CURRENT'

@pytest.mark.parametrize('text,code',[
  ('make the second campaign 5000','update_plan_allocation'),
  ('set second campaign to 5000','update_plan_allocation'),
  ('increase the total budget by 100','adjust_plan_budget'),
  ('split the rest equally','distribute_remaining'),
  ('split equally','rebalance_plan'),
  ('undo that','undo_plan_change'),
  ('remove third campaign','remove_plan_item'),
])
def test_core_commands(text,code):
    assert classify_plan_command(text)['type']==code

def test_missing_plan_clarifies():
    r=run_workflow(ChatRequest(message='increase the second campaign by 100'))
    assert r.mode=='clarification'
    assert 'select' in r.reply.lower()

def test_wrong_ordinal_clarifies():
    r=run_workflow(ChatRequest(message='increase the fifth campaign by 100',current_plan=plan()))
    assert r.mode=='clarification'
    assert '3 campaigns' in r.reply

def test_foreign_currency_rejected():
    r=run_workflow(ChatRequest(message='add ₦100 to the second campaign',current_plan=plan()))
    assert r.mode=='clarification'
    assert 'NGN' in r.reply and 'USD' in r.reply

def test_no_payment_tools():
    r=run_workflow(ChatRequest(message='add 100 to second campaign',current_plan=plan()))
    assert r.action_proposal and 'checkout' not in r.action_proposal['type']


def test_real_event_discovery():
    r=run_workflow(ChatRequest(message='show three events',resources=[
        PlatformResource(id=1,title='Health Workshop',kind='event',location='Abuja'),
        PlatformResource(id=2,title='Tree Planting',kind='event',location='Lagos')]))
    assert r.mode=='platform_search'
    assert len(r.resources)==2
    assert r.resources[0].title=='Health Workshop'

def test_unconnected_service_never_invents():
    r=run_workflow(ChatRequest(message='show service providers in Abuja',resources=[]))
    assert r.mode=='platform_search'
    assert not r.resources
    assert 'matching service' in r.reply.lower() and 'current listings' in r.reply.lower()

def test_general_knowledge_is_allowed_without_search(monkeypatch):
    import app.graph as graph
    class KnowledgeOnly:
        def invoke(self, payload, config=None):
            return {'reply':'The Joker is a fictional comic-book character.',
                    'agents_run':['Supervisor','Knowledge'], 'decision':{'route':'knowledge'}}
    monkeypatch.setattr(graph,'_GRAPH',KnowledgeOnly())
    r=run_workflow(ChatRequest(message='who is joker?'))
    assert 'Joker' in r.reply and not r.resources

def test_followup_infers_previous_currency():
    c=[Campaign(id=i,title=f'Healthcare #{i}',currency='USD') for i in [34,23,46]]
    r=run_workflow(ChatRequest(message='add three of them to donate 10000',campaigns=c,recent_campaign_ids=[34,23,46],current_plan=plan()))
    assert r.plan_proposal.currency=='USD'
    assert sum(i.amount for i in r.plan_proposal.items)==10000

def test_one_instruction_find_and_allocate():
    c=[Campaign(id=i,title=f'Healthcare {i}',category='Healthcare',currency='USD') for i in [11,12,13,14,15]]
    r=run_workflow(ChatRequest(message='find five healthcare campaigns, choose top three and give 20000',campaigns=c))
    assert r.mode=='multi_step_plan'
    assert len(r.plan_proposal.items)==3
    assert r.plan_proposal.currency=='USD'
    assert sum(i.amount for i in r.plan_proposal.items)==20000


def test_simple_donation_draft():
    c=[Campaign(id=i,title=f'Healthcare {i}',category='Healthcare',currency='NGN') for i in [11,12,13]]
    r=run_workflow(ChatRequest(message='I want to donate ₦20000 to healthcare campaigns',campaigns=c))
    assert r.plan_proposal.currency=='NGN' and r.plan_proposal.budget==20000
    assert len(r.plan_proposal.items)==3


def test_append_more_does_not_replace_existing_plan():
    c=[Campaign(id=i,title=f'Education {i}',category='Education',currency='USD') for i in [4,5,6,7]]
    current=CurrentPlan(currency='USD',budget=8000,items=[CurrentPlanItem(id=4,amount=8000)])
    r=run_workflow(ChatRequest(message='add two more education campaigns',current_plan=current,campaigns=c))
    assert r.action_proposal['type']=='append_plan_campaigns'
    assert r.action_proposal['campaign_ids']==[5,6]


def test_multi_step_rejects_currency_conversion():
    c=[Campaign(id=i,title=f'Healthcare {i}',category='Healthcare',currency='USD') for i in [11,12,13]]
    r=run_workflow(ChatRequest(message='find three healthcare campaigns and allocate ₦20000',campaigns=c))
    assert r.plan_proposal is None
    assert r.mode=='clarification'


def test_missing_real_cause_not_fabricated():
    c=[Campaign(id=11,title='School Kits',category='Education',currency='NGN')]
    r=run_workflow(ChatRequest(message='find three healthcare campaigns and split ₦3000',campaigns=c))
    assert r.plan_proposal is None
