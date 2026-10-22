"""Donor rankings: real admin rows vs public non-identifying summary."""
from app.graph import run_workflow
from app.schemas import ChatRequest, RankingEvidence


def make_evidence(**overrides):
    payload={'type':'individual','period':'all_time','status':'published','verified':True,
             'rows':[],'total':0,'summary':{'currency':'USD','donations':80,
                                          'contributors':11,'amount':177500.0},
             'message':'No public names available.'}
    payload.update(overrides)
    return RankingEvidence.model_validate(payload)


def test_public_aggregate_giving_is_not_presented_as_named_ranking():
    result=run_workflow(ChatRequest(message='show me top 10 donors',ranking_data=make_evidence()))
    assert result.mode=='ranking_summary'
    assert '80 recorded paid donation' in result.reply
    assert 'USD 177,500' in result.reply
    assert 'not a Top 10 of named donors' in result.reply
    assert not result.action_proposal and not result.campaign_ids


def test_private_admin_ranking_uses_only_actual_gateway_rows():
    evidence=make_evidence(summary=None,scope='administrator',total=2,
                          rows=[{'rank':1,'title':'Fictional Test Supporter',
                                 'score':5000,'category':'Recorded · USD'}])
    result=run_workflow(ChatRequest(message='show me top 10 donors',ranking_data=evidence))
    assert result.mode=='ranking_public'
    assert 'administrator-only' in result.reply
    assert '1 administrator-only' in result.reply
    # The AI must not hallucinate a 10-person list or unverified participant.
    assert 'Fictional Test Supporter' not in result.reply


def test_no_summary_does_not_fabricate_a_leaderboard():
    result=run_workflow(ChatRequest(message='show top 10 donors',
                                   ranking_data=make_evidence(summary=None)))
    assert result.mode=='ranking_empty'
    assert result.campaign_ids==[]
