from app.intent_guard import assess,parse_plan_action

def test_offtopic():
    assert assess('what is the best time to sleep')=='off_topic'
    assert assess('who is joker')=='off_topic'
    assert assess('write python code to do stuff')=='off_topic'

def test_plan_draft_actions():
    assert parse_plan_action('update the donation amount to ₦10000')=={'type':'update_plan_budget','amount':10000,'currency':'NGN'}
    assert parse_plan_action('change my donation budget to ₦10,000')['amount']==10000
    assert parse_plan_action('update the donation amount to 10000')['currency']=='CURRENT'
    assert parse_plan_action('remove the second campaign')['position']==2
    assert parse_plan_action('allocate ₦7,000 to the first campaign')['amount']==7000
    assert parse_plan_action('undo the last change')['type']=='undo_plan_change'
    assert parse_plan_action('remove all the existing plan')['type']=='clear_plan'
    assert parse_plan_action('pay now') is None
