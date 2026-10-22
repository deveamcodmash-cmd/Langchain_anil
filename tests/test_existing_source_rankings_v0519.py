"""Existing-data leaderboard responses must use signed, visible source records."""
from app.graph import run_workflow
from app.schemas import ChatRequest, RankingContext, RankingEvidence
from app.ranking_intelligence import ranking_intent


def test_follower_ranking_with_source_data():
    evidence=RankingEvidence(status='published',type='followers',period='all_time',verified=True,total=2,
        rows=[{'rank':1,'title':'Community Advocate','score':40,'category':'Followers'},
              {'rank':2,'title':'Another Advocate','score':30,'category':'Followers'}],
        message='Published Profiles · Recorded Followers.')
    response=run_workflow(ChatRequest(message='show top 10 followers',ranking_data=evidence,
        ranking_context=RankingContext(type='followers',count=10)))
    assert response.mode=='ranking_public'
    assert '2 currently eligible' in response.reply
    assert response.campaign_ids==[]


def test_follower_ranking_empty_does_not_invent_names():
    evidence=RankingEvidence(status='published',type='followers',period='all_time',verified=True,total=0,rows=[])
    response=run_workflow(ChatRequest(message='show top followers',ranking_data=evidence))
    assert response.mode=='ranking_empty' and response.campaign_ids==[]


def test_unsupported_follower_filter_rejected():
    evidence=RankingEvidence(status='published',type='followers',period='all_time',verified=True,total=1,
        rows=[{'rank':1,'title':'Someone','score':99}])
    response=run_workflow(ChatRequest(message='top followers in Nigeria',ranking_data=evidence,
        ranking_context=RankingContext(type='followers',unsupported_filter=True)))
    assert response.mode=='ranking_pending'
    assert 'Nigeria' not in response.reply or 'leaderboard' in response.reply


def test_ranking_requests_still_distinct_from_general_questions():
    assert ranking_intent('show me top 10 donors')
    assert ranking_intent('show me top followers')
    assert not ranking_intent('what is the best movie this week?')
