"""Screenshot regressions: a follow-up updates the active draft, not search results."""
import pytest

from app.graph import run_workflow
from app.plan_intelligence import classify_plan_command
from app.plan_context import resolve_plan_followup
from app.plan_semantics import (PlanInterpretation,decode_safe_interpretation,
                                semantic_plan_edit,written_amounts)
from app.schemas import ChatRequest,CurrentPlan,CurrentPlanItem,ConversationMessage


@pytest.fixture
def plan():
    return CurrentPlan(currency='USD',budget=12000,items=[
        CurrentPlanItem(id=13,amount=8000),CurrentPlanItem(id=22,amount=4000)])


@pytest.mark.parametrize('message',[
    'decrease the total budget to 9000',
    'please reduce my budget to 9,000',
    'set the total to $9000',
    'yes adjust the amount and decrease to 9000',
    'change my giving plan budget to 9000',
    'lower the budget to USD 9000',
    'make the total budget 9000',
])
def test_direct_budget_update_uses_current_draft(message,plan):
    response=run_workflow(ChatRequest(message=message,current_plan=plan))
    assert response.mode=='action_proposed'
    assert response.action_proposal=={'type':'update_plan_budget','amount':9000,'currency':('USD' if ('USD' in message or '$' in message) else 'CURRENT')}
    assert response.plan_proposal is None
    assert response.campaign_ids==[]
    assert [i.id for i in plan.items]==[13,22]


def test_yes_followup_continues_previous_budget_request(plan):
    request=ChatRequest(message='yes',current_plan=plan,history=[
        ConversationMessage(role='user',content='decrease the total budget to 9000'),
        ConversationMessage(role='assistant',content='How would you like to adjust the amounts?'),
    ])
    reply=run_workflow(request)
    assert reply.action_proposal=={'type':'update_plan_budget','amount':9000,'currency':'USD'}
    assert reply.plan_proposal is None


def test_currency_answer_completes_previous_instruction(plan):
    request=ChatRequest(message='usd',current_plan=plan,history=[
        ConversationMessage(role='user',content='decrease the total budget to 9000'),
        ConversationMessage(role='assistant',content='Which currency should the giving plan use?'),
    ])
    reply=run_workflow(request)
    assert reply.action_proposal=={'type':'update_plan_budget','amount':9000,'currency':'USD'}
    assert reply.campaign_ids==[]


def test_exact_three_message_screenshot_chain(plan):
    request=ChatRequest(message='USD',current_plan=plan,history=[
        ConversationMessage(role='user',content='decrease the total budget to 9000'),
        ConversationMessage(role='assistant',content='Please confirm your currency and allocation preferences.'),
        ConversationMessage(role='user',content='yes adjust the amount and decrease to 9000'),
        ConversationMessage(role='assistant',content='These campaigns use different currencies. Which currency should the plan use?'),
    ])
    reply=run_workflow(request)
    assert reply.mode=='action_proposed'
    assert reply.action_proposal=={'type':'update_plan_budget','amount':9000,'currency':'USD'}


def test_currency_mismatch_does_not_convert_or_replace_campaigns(plan):
    request=ChatRequest(message='NGN',current_plan=plan,history=[
        ConversationMessage(role='user',content='lower the budget to 9000'),
        ConversationMessage(role='assistant',content='Which currency should I use?'),
    ])
    reply=run_workflow(request)
    assert reply.mode=='clarification'
    assert reply.action_proposal is None
    assert reply.plan_proposal is None
    assert 'USD' in reply.reply and 'NGN' in reply.reply


def test_unprompted_currency_keeps_current_plan(plan):
    reply=resolve_plan_followup(ChatRequest(message='usd',current_plan=plan,history=[
        ConversationMessage(role='user',content='what causes are popular'),
        ConversationMessage(role='assistant',content='Here are some causes.'),
    ]))
    assert reply.action_proposal is None
    assert reply.mode=='contextual_clarification'


def test_yes_is_not_authorization_after_unrelated_chat(plan):
    assert resolve_plan_followup(ChatRequest(message='yes',current_plan=plan,history=[
        ConversationMessage(role='user',content='show me disaster relief campaigns'),
        ConversationMessage(role='assistant',content='Would you like a regional list?'),
    ])) is None


@pytest.mark.parametrize('phrase,kind',[
    ('reduce the total budget by 1000','adjust_plan_budget'),
    ('increase second campaign by 200','adjust_plan_allocation'),
    ('remove the last campaign','remove_plan_item'),
    ('rebalance the plan equally','rebalance_plan'),
])
def test_existing_position_and_delta_commands_remain_distinct(phrase,kind):
    assert classify_plan_command(phrase)['type']==kind


def test_semantic_interpreter_rejects_hallucinated_amount(plan):
    req=ChatRequest(message='lower this budget to 9000',current_plan=plan)
    result=decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=8000,confident=True))
    assert result is None


def test_semantic_interpreter_accepts_model_paraphrase_with_verified_amount(plan):
    req=ChatRequest(message='please adjust the plan budget down to 9k',current_plan=plan)
    result=decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=9000,confident=True))
    assert result.action_proposal=={'type':'update_plan_budget','amount':9000,'currency':'CURRENT'}


def test_semantic_interpreter_rejects_fake_campaign_position(plan):
    req=ChatRequest(message='decrease the first allocation by 100',current_plan=plan)
    result=decode_safe_interpretation(req,PlanInterpretation(action='adjust_selected_by',amount=100,position=3,direction='decrease',confident=True))
    assert result is None


def test_semantic_interpreter_avoids_new_cause_intent(plan):
    req=ChatRequest(message='make a donation of 9000 to education campaigns',current_plan=plan)
    result=decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=9000,confident=True))
    assert result is None


def test_semantic_interpreter_rejects_unstated_currency_conversion(plan):
    req=ChatRequest(message='reduce budget to NGN 9000',current_plan=plan)
    result=decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=9000,confident=True))
    assert result.mode=='clarification'
    assert result.action_proposal is None


def test_amount_parser_with_k_and_commas():
    assert written_amounts('make the plan total 9k or 12,500')=={9000,12500}


def test_yes_does_not_replay_already_confirmed_action(plan):
    r=resolve_plan_followup(ChatRequest(message='yes',current_plan=plan,history=[
        ConversationMessage(role='user',content='decrease the total budget to 9000'),
        ConversationMessage(role='assistant',content='Your giving plan budget is now USD 9000. No payment was made.'),
    ]))
    assert r is None


def test_semantic_prevents_unmentioned_selected_position(plan):
    req=ChatRequest(message='please remove a campaign from this plan',current_plan=plan)
    assert decode_safe_interpretation(req,PlanInterpretation(action='remove_selected',position=2,confident=True)) is None


def test_semantic_prevents_hijacking_new_plan_request(plan):
    req=ChatRequest(message='please make a new plan for 9000',current_plan=plan)
    assert decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=9000,confident=True)) is None


def test_semantic_does_not_execute_explanatory_question(plan):
    req=ChatRequest(message='how can i reduce the plan budget to 9000',current_plan=plan)
    assert decode_safe_interpretation(req,PlanInterpretation(action='set_total',amount=9000,confident=True)) is None


def test_already_matching_total_is_not_claimed_as_new_update(plan):
    reply=run_workflow(ChatRequest(message='reduce the total budget to 12000',current_plan=plan))
    assert reply.action_proposal is None
    assert reply.mode=='contextual_clarification'
    assert 'already totals USD 12,000' in reply.reply
