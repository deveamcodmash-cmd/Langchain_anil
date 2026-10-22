"""Verified rankings cannot be hallucinated or conflated across currencies."""
import pytest
from app.schemas import ChatRequest, RankingEvidence, RankingContext
from app.graph import run_workflow
from app.ranking_intelligence import ranking_intent


def request(text, board=None, context=None):
    return ChatRequest(message=text,ranking_data=board,ranking_context=context)


@pytest.mark.parametrize('question', [
    'show me top 10 donors','which corporate are donating the most',
    'show top service providers','who donated the most',
    'top 5 charity contributors', 'where do i rank',
])
def test_ranking_questions_never_fabricate_people(question):
    out=run_workflow(request(question))
    assert out.mode=='ranking_pending'
    assert out.campaign_ids==[] and out.resources==[]
    assert 'not published' in out.reply


def test_verified_provider_snapshot_is_usable_only_with_evidence():
    board=RankingEvidence(status='published',type='providers',period='all_time',verified=True,total=2,
      rows=[dict(rank=1,title='North Wellness',score=91.2,category='Wellness'),
            dict(rank=2,title='East Support',score=88.3)])
    out=run_workflow(request('show top 10 service providers',board))
    assert out.mode=='ranking_public'
    assert out.campaign_ids==[]
    assert '2 currently eligible' in out.reply
    assert 'North Wellness' not in out.reply  # names only appear in trusted UI cards


def test_hallucinated_unverified_board_is_rejected():
    board=RankingEvidence(status='published',type='providers',period='all_time',verified=False,total=10,
      rows=[dict(rank=1,title='Fake Provider',score=100)])
    out=run_workflow(request('top 10 providers',board))
    assert out.mode=='ranking_pending'


def test_ranking_followup_uses_validated_context():
    ctx=RankingContext(type='corporate',count=10,period='year')
    board=RankingEvidence(status='not_published',type='corporate',period='last_month')
    out=run_workflow(request('show last month',board,ctx))
    assert out.mode=='ranking_pending'


def test_ordinary_movie_question_is_not_ranking():
    assert not ranking_intent('what are the best movies to watch this weekend')


def test_ranking_evidence_rejects_untrusted_extra_fields():
    with pytest.raises(Exception):
        RankingEvidence(status='published',type='providers',rows=[dict(rank=1,title='Company',score=10, email='hidden@example.com')],verified=True)
