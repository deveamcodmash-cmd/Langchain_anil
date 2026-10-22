"""Multi-step contextual draft changes are one atomic, grounded proposal."""
import pytest
from app.graph import run_workflow
from app.schemas import ChatRequest,CurrentPlan,CurrentPlanItem
from app.compound_plan import CandidateStep,CandidateTransaction,validate_candidate_transaction

@pytest.fixture
def plan():
    return CurrentPlan(currency='USD',budget=12000,items=[CurrentPlanItem(id=13,amount=8000),CurrentPlanItem(id=22,amount=4000)])

def request(text,plan):
    return ChatRequest(message=text,current_plan=plan)

def test_remove_and_reduce_is_not_single_campaign_allocation(plan):
    response=run_workflow(request('remove the second campaign and decrease the total budget to 9000',plan))
    assert response.action_proposal['type']=='plan_transaction'
    assert [s['type'] for s in response.action_proposal['steps']]==['remove_plan_item','update_plan_budget']
    assert response.action_proposal['steps'][0]['campaign_id']==22
    assert response.action_proposal['steps'][1]['amount']==9000
    assert response.plan_proposal is None and response.campaign_ids==[]
    assert plan.items[1].amount==4000

def test_reverse_order_keeps_action_sequence(plan):
    response=run_workflow(request('decrease total budget to 9000 and remove first campaign',plan))
    assert response.action_proposal['steps'][0]['amount']==9000
    assert response.action_proposal['steps'][1]['campaign_id']==13

@pytest.mark.parametrize('text',[
    'what if I remove second campaign and decrease the total budget to 9000',
    'how would I remove second campaign and decrease the total budget to 9000',
    'remove the second campaign and decrease total to NGN 9000',
    'remove third campaign and decrease the total budget to 9000',
    'remove second campaign and decrease the total budget to 0',
])
def test_unsafe_or_hypothetical_does_not_propose_transaction(plan,text):
    response=run_workflow(request(text,plan))
    assert not response.action_proposal or response.action_proposal.get('type')!='plan_transaction'

def test_model_interpreter_can_understand_novel_expression(plan):
    req=request('ditch the second campaign and bring total spending down to 9k',plan)
    candidate=CandidateTransaction(confident=True,steps=[
        CandidateStep(type='remove_plan_item',position=2),
        CandidateStep(type='update_plan_budget',amount=9000),
    ])
    result=validate_candidate_transaction(req,candidate)
    assert result and result.action_proposal['type']=='plan_transaction'

def test_model_cannot_invent_campaign_position(plan):
    req=request('ditch the second campaign and bring total spending down to 9k',plan)
    candidate=CandidateTransaction(confident=True,steps=[CandidateStep(type='remove_plan_item',position=1),CandidateStep(type='update_plan_budget',amount=9000)])
    assert validate_candidate_transaction(req,candidate) is None

def test_model_cannot_invent_monetary_values(plan):
    req=request('ditch the second campaign and bring total spending down to 9k',plan)
    candidate=CandidateTransaction(confident=True,steps=[CandidateStep(type='remove_plan_item',position=2),CandidateStep(type='update_plan_budget',amount=8000)])
    assert validate_candidate_transaction(req,candidate) is None

def test_model_cannot_convert_currency(plan):
    req=request('remove second campaign and decrease total to NGN 9000',plan)
    candidate=CandidateTransaction(confident=True,steps=[CandidateStep(type='remove_plan_item',position=2),CandidateStep(type='update_plan_budget',amount=9000)])
    assert validate_candidate_transaction(req,candidate) is None

def test_model_hypothetical_not_an_action(plan):
    req=request('what if I remove second campaign and decrease total to 9000',plan)
    candidate=CandidateTransaction(confident=True,steps=[CandidateStep(type='remove_plan_item',position=2),CandidateStep(type='update_plan_budget',amount=9000)])
    assert validate_candidate_transaction(req,candidate) is None


def test_comma_separated_amount_does_not_split_number(plan):
    result=run_workflow(request('remove the second campaign and lower the total budget to 9,000',plan))
    assert result.action_proposal['type']=='plan_transaction'
    assert result.action_proposal['steps'][-1]['amount']==9000


def test_unsupported_multi_edit_does_not_become_wrong_single_allocation(plan):
    result=run_workflow(request('remove the second campaign and lower the total budget to 9k',plan))
    assert result.action_proposal is None
    assert result.mode=='clarification'
    assert 'both' in result.reply.lower()
