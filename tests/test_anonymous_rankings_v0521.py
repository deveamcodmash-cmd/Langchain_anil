from app.schemas import ChatRequest,RankingEvidence,RankingRow
from app.ranking_intelligence import answer_ranking

def test_anonymous_ranked_rows_are_supported_without_scores():
    evidence=RankingEvidence(status='published',type='individual',period='all_time',verified=True,
        total=8,rows=[RankingRow(rank=1,title='Supporter 1 · Identity Hidden',score=None,category='Recorded · USD · Hidden Amount'),
                     RankingRow(rank=2,title='Supporter 2 · Identity Hidden',score=None,category='Recorded · USD · Hidden Amount')])
    r=answer_ranking(ChatRequest(message='show me top 10 donors',ranking_data=evidence))
    assert r.mode=='ranking_public'
    assert 'anonymous positions' in r.reply.lower()
    assert r.plan_proposal is None and r.campaign_ids==[]


def test_no_verified_ranks_still_remains_empty():
    evidence=RankingEvidence(status='published',type='individual',period='all_time',verified=True,rows=[],total=0)
    r=answer_ranking(ChatRequest(message='show top donors',ranking_data=evidence))
    assert r.mode=='ranking_empty'
