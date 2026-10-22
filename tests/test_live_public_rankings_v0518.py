"""Public recorded-leaderboard copy must not claim bank-audited giving."""
from app.graph import run_workflow
from app.schemas import ChatRequest, RankingEvidence

def test_public_campaign_reported_amount_is_not_called_reconciled():
    evidence=RankingEvidence(status='published',type='campaigns',period='all_time',verified=True,total=1,
        rows=[{'rank':1,'title':'School Support','score':12000,'category':'Recorded · USD'}],
        message='Published Campaigns — Source-Reported Raised Amounts (Not Bank-Reconciled).')
    response=run_workflow(ChatRequest(message='show top 10 campaigns',ranking_data=evidence))
    assert response.mode=='ranking_public'
    assert 'Source-Reported' in response.reply
    assert 'verified donations' not in response.reply.lower()
    assert response.campaign_ids==[]


def test_no_named_public_participants_is_not_fake_top10():
    evidence=RankingEvidence(status='published',type='individual',period='all_time',verified=True,total=0,
        rows=[],message='No Public Participants Yet.')
    response=run_workflow(ChatRequest(message='show me top 10 donors',ranking_data=evidence))
    assert response.mode=='ranking_empty'
    assert response.campaign_ids==[]
