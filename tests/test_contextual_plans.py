"""Regression coverage: exactly the multi-turn failure reported in Filantrophy."""
from app.followup import contextual_plan
from app.graph import run_workflow
from app.schemas import ChatRequest, Campaign

CAMPAIGNS = [Campaign(id=i,title=name,category='Healthcare',currency='USD') for i,name in [
    (34,'Healthcare Fundraiser'),
    (23,'Free Eye Care for Rural Communities'),
    (46,'Safer Beginnings for Mothers and Babies'),
]]

def req(message, recent=None, campaigns=None):
    return ChatRequest(message=message,recent_campaign_ids=[34,23,46] if recent is None else recent,
                       campaigns=CAMPAIGNS if campaigns is None else campaigns)

def test_add_three_from_previous_display_usd_auto_proposal_without_llm():
    out=run_workflow(req('add three of them to donate 10000'))
    assert out.mode=='contextual_plan'
    assert out.plan_proposal is not None
    assert out.plan_proposal.currency=='USD'
    assert out.plan_proposal.budget==10000
    assert [(i.id,i.amount) for i in out.plan_proposal.items]==[(34,3334),(23,3333),(46,3333)]
    assert out.campaign_ids == []  # Do not repeat 3 cards on follow-up
    assert 'No payment has been made' in out.reply

def test_explicit_ngn_mismatch_asks_without_converting():
    out=contextual_plan(req('Donate ₦10,000 to those three'))
    assert out.plan_proposal is None
    assert 'USD' in out.reply and 'NGN' in out.reply
    assert out.mode=='contextual_clarification'

def test_when_previous_results_missing_dont_invent():
    out=contextual_plan(req('Donate 10000 to those three', recent=[]))
    assert out.plan_proposal is None
    assert 'show or select' in out.reply

def test_missing_eligible_campaign_prevents_partial_plan():
    out=contextual_plan(req('add three of them to donate 10000',campaigns=CAMPAIGNS[:2]))
    assert out.plan_proposal is None
    assert 'no longer available' in out.reply

def test_mixed_currency_prevents_incorrect_one_payment():
    mixed=[c.model_copy(update={'currency':'NGN'}) if c.id==23 else c for c in CAMPAIGNS]
    out=contextual_plan(req('add three of them to donate 10000',campaigns=mixed))
    assert out.plan_proposal is None
    assert 'different currencies' in out.reply

def test_two_of_three_is_ambiguous():
    out=contextual_plan(req('add two of them to donate 10000'))
    assert out.plan_proposal is None
    assert 'Which 2' in out.reply

def test_first_two_is_explicit():
    out=contextual_plan(req('allocate 10000 to the first two'))
    assert out.plan_proposal is not None
    assert [(i.id,i.amount) for i in out.plan_proposal.items]==[(34,5000),(23,5000)]

def test_all_shown_is_three():
    out=contextual_plan(req('Split $10000 between all of them'))
    assert out.plan_proposal is not None
    assert len(out.plan_proposal.items)==3

def test_missing_budget_requests_it():
    out=contextual_plan(req('add those three campaigns to my giving plan'))
    assert out.plan_proposal is None
    assert 'How much' in out.reply

def test_unrelated_question_not_caught():
    assert contextual_plan(req('Show me another healthcare campaign')) is None

def test_do_not_guess_subgroup_currency():
    out=contextual_plan(req('donate NGN 10000 to them'))
    assert out.plan_proposal is None
    assert 'but you requested NGN' in out.reply

def test_general_knowledge_reaches_agent_instead_of_scope_refusal(monkeypatch):
    import app.graph as graph
    class KnowledgeOnly:
        def invoke(self, payload, config=None):
            return {'reply':'The Joker is a fictional Batman villain.',
                    'agents_run':['Supervisor','Knowledge'], 'decision':{'route':'knowledge'}}
    monkeypatch.setattr(graph,'_GRAPH',KnowledgeOnly())
    out=run_workflow(req('who is joker'))
    assert 'Joker' in out.reply
    assert out.mode!='out_of_scope' 

def test_signed_api_returns_exact_prior_campaign_plan_without_openai():
    import hashlib, hmac, json, time, uuid, os
    from fastapi.testclient import TestClient
    from app.main import app
    secret='test-followup-secret-more-than-thirty-two-characters'
    os.environ['FILANTROPHY_SHARED_SECRET']=secret
    payload={'message':'add three of them to donate 10000',
             'recent_campaign_ids':[34,23,46],
             'campaigns':[c.model_dump() for c in CAMPAIGNS]}
    body=json.dumps(payload).encode()
    ts=str(int(time.time()))
    nonce=uuid.uuid4().hex
    mac=hmac.new(secret.encode(), f'{ts}.{nonce}.'.encode()+body,hashlib.sha256).hexdigest()
    result=TestClient(app).post('/v1/chat',content=body,headers={
        'X-Filantrophy-Timestamp':ts,
        'X-Filantrophy-Nonce':nonce,
        'X-Filantrophy-Signature':'sha256='+mac,
        'Content-Type':'application/json'})
    assert result.status_code==200,result.text
    data=result.json()
    assert data['mode']=='contextual_plan'
    assert data['plan_proposal']['currency']=='USD'
    assert data['plan_proposal']['budget']==10000
    assert [x['id'] for x in data['plan_proposal']['items']]==[34,23,46]
    assert data['campaign_ids']==[]
