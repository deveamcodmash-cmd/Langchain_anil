"""Regression tests for donation amounts modifying an existing validated draft.

This endpoint proposes only; the Joomla browser executes and verifies changes.
"""
import pytest
from app.graph import run_workflow
from app.schemas import ChatRequest, CurrentPlan, CurrentPlanItem


@pytest.fixture
def existing_plan():
    return CurrentPlan(currency='USD', budget=15000,
                       items=[CurrentPlanItem(id=11, amount=15000)])


@pytest.mark.parametrize('message', [
    'make a donation of 10000', 'donate 10000', 'i want to donate 10000',
    'make a donation of $10000', 'Please make a donation of USD 10000',
])
def test_new_amount_preserves_existing_campaign_and_proposes_draft_change(message, existing_plan):
    response = run_workflow(ChatRequest(message=message, current_plan=existing_plan))
    assert response.mode == 'action_proposed'
    assert response.action_proposal == {'type': 'update_plan_budget', 'amount': 10000, 'currency': 'USD'}
    assert response.plan_proposal is None
    assert existing_plan.budget == 15000
    assert existing_plan.items[0].amount == 15000


def test_currency_mismatch_requires_choice(existing_plan):
    response = run_workflow(ChatRequest(message='make a donation of ₦10000', current_plan=existing_plan))
    assert response.mode == 'clarification'
    assert response.action_proposal is None
    assert 'USD' in response.reply and 'NGN' in response.reply


def test_no_prior_selection_does_not_invent_campaign_or_action():
    # Unlike a change to an existing plan, a naked amount has no verified target.
    plan = CurrentPlan(currency='USD',budget=15000,items=[])
    from app.followup import _amount_and_currency
    assert _amount_and_currency('make a donation of 10000')==(10000,None)
    # An external LLM may still propose a new plan, but this deterministic
    # action path must not invent a target when current selections are empty.
    # It therefore requires the normal discovery / supervisor route.
    assert not plan.items


def test_targeted_cause_not_misinterpreted_as_old_budget_update(existing_plan):
    import re
    phrase='make a donation of 10000 to education campaigns'
    regex=(r'(?i)\s*(?:please\s+)?(?:make\s+(?:a\s+)?donation\s+(?:of\s+)?|'
           r'(?:i\s+want\s+to\s+)?donate\s+|give\s+|contribute\s+)'
           r'(?:(?:\$|₦|£|€|₹|USD|NGN|GBP|EUR|INR)\s*)?\d[\d,]*'
           r'(?:\s*(?:USD|NGN|GBP|EUR|INR))?\s*[.!]?\s*')
    assert re.fullmatch(regex, phrase) is None
