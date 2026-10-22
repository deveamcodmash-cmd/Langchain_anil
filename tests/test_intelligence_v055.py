"""No network: regressions for the data/intent/answer contract.

These tests don't claim a real LLM can classify 10k unseen expressions.
They test that semantic classifications and retrieved IDs are handled safely.
"""
from __future__ import annotations

import json
import sys
import types

import pytest
from app.intelligence import normalize_decision, compact_history, is_repeated_reply, evidence_notice
from app.schemas import ChatRequest


@pytest.mark.parametrize('intent,expected', [
    ('campaign_discovery','discovery'),
    ('donation_explanation','knowledge'),
    ('current_world_information','knowledge'),
    ('popularity_comparison','knowledge'),
    ('platform_explanation','knowledge'),
    ('giving_plan','plan'),
    ('unrelated','knowledge'),
    ('unspecified','discovery'),
])
def test_intent_is_authoritative_over_inconsistent_route(intent, expected):
    result=normalize_decision({'intent':intent,'route':'discovery'})
    assert result['route']==expected


@pytest.mark.parametrize('phrase', [
    'I could not find a matching eligible published campaign in the available catalogue. Try a different cause or location.',
    'I could not find a matching eligible published campaign in the available catalogue. Try a different cause or location!',
])
def test_repeated_loop_detected(phrase):
    history=[{'role':'assistant','content':'I could not find a matching eligible published campaign in the available catalogue. Try a different cause or location.'}]
    assert is_repeated_reply(phrase,history)
    assert not is_repeated_reply('Are you asking about donation amounts or progress?',history)


def test_compact_history_preserves_latest_user_question_and_deduplicates_error():
    history=[
        {'role':'user','content':'search disaster areas'},
        {'role':'assistant','content':'Not found.'},
        {'role':'user','content':'how is the donation amount'},
        {'role':'assistant','content':'Not found.'},
        {'role':'user','content':'what is current disaster'},
    ]
    result=compact_history(history)
    assert [x['content'] for x in result if x['role']=='user'] == [
        'search disaster areas','how is the donation amount','what is current disaster']
    assert sum(x['content']=='Not found.' for x in result)==1


def test_real_time_and_popularity_facts_require_evidence():
    assert 'no verified live disaster-news' in evidence_notice('current_world_information')
    assert 'no verified donation velocity' in evidence_notice('popularity_comparison')


@pytest.fixture()
def install_fake_graph(monkeypatch):
    """Isolated LangGraph test double executing the real node functions."""
    class FakeStateGraph:
        def __init__(self,*args):self.nodes={};self.edges={};self.branches={};self.entry=None
        def add_node(self,n,f):self.nodes[n]=f
        def add_edge(self,n,target):self.edges[n]=target
        def add_conditional_edges(self,n,f,mapping):self.branches[n]=(f,mapping)
        def set_entry_point(self,n):self.entry=n
        def compile(self):return self
        def invoke(self,state,config=None):
            current=self.entry
            for _ in range(20):
                if current=='__END__':return state
                state.update(self.nodes[current](state))
                if current in self.branches:
                    f,mapping=self.branches[current];current=mapping[f(state)]
                else:current=self.edges[current]
            raise AssertionError('Graph did not end')

    class FakeMessage:
        def __init__(self,content):self.content=content

    class FakeModel:
        next_intent='unspecified'
        next_route='discovery'
        semantic_ids=[]
        received=[]
        generated_reply='I can help you explore that.'
        def __init__(self,*args,**kwargs):pass
        def with_structured_output(self,schema):
            class Output:
                def invoke(self,msgs):
                    if schema.__name__=='Decision':
                        return schema(intent=FakeModel.next_intent,route=FakeModel.next_route,desired_count=3)
                    return schema(matching_ids=FakeModel.semantic_ids)
            return Output()
        def invoke(self,msgs):
            FakeModel.received.append(msgs)
            return types.SimpleNamespace(content=FakeModel.generated_reply)

    gmod=types.ModuleType('langgraph.graph');gmod.StateGraph=FakeStateGraph;gmod.END='__END__'
    messages=types.ModuleType('langchain_core.messages')
    messages.SystemMessage=FakeMessage;messages.HumanMessage=FakeMessage;messages.AIMessage=FakeMessage
    monkeypatch.setitem(sys.modules,'langgraph',types.ModuleType('langgraph'))
    monkeypatch.setitem(sys.modules,'langgraph.graph',gmod)
    monkeypatch.setitem(sys.modules,'langchain_core',types.ModuleType('langchain_core'))
    monkeypatch.setitem(sys.modules,'langchain_core.messages',messages)
    monkeypatch.setitem(sys.modules,'langchain_openai',types.SimpleNamespace(ChatOpenAI=FakeModel))
    monkeypatch.setenv('OPENAI_API_KEY','offline-tests-only')
    from app import graph
    monkeypatch.setattr(graph,'_GRAPH',None)
    yield FakeModel, graph
    graph._GRAPH=None


@pytest.mark.parametrize('message,intent', [
    ('how is the donation amount','donation_explanation'),
    ('what current disaster where I can donate','current_world_information'),
    ('what current hot donation','popularity_comparison'),
    ('which donations are trending','popularity_comparison'),
    ('what amount should i donate?','donation_explanation'),
    ('how much can I give?','donation_explanation'),
])
def test_information_intents_cannot_trigger_campaign_no_match_reply(install_fake_graph,message,intent):
    Fake, graph=install_fake_graph
    Fake.next_intent=intent;Fake.next_route='discovery';Fake.received=[]
    Fake.generated_reply='The donation details depend on the campaign you select.'
    response=graph.run_workflow(ChatRequest(message=message,history=[
        {'role':'user','content':'I want to donate search disaster areas'},
        {'role':'assistant','content':'I could not find a matching eligible published campaign in the available catalogue.'},
    ]))
    assert response.reply==Fake.generated_reply
    assert 'Knowledge' in response.agents_run
    assert 'Discovery' not in response.agents_run
    assert len(Fake.received)==1
    assert intent in str(Fake.received[0][-1].content)


def test_semantic_fallback_only_returns_trusted_campaign_ids(install_fake_graph):
    Fake,graph=install_fake_graph
    Fake.next_intent='campaign_discovery';Fake.next_route='discovery';Fake.semantic_ids=[23,999,23,22]
    Fake.generated_reply='Here are relevant verified campaigns.'
    request=ChatRequest(message='support communities affected by severe weather', campaigns=[
        {'id':23,'title':'Flood Emergency Response','category':'Relief','summary':'Families affected by flooding','currency':'USD'},
        {'id':22,'title':'Storm Recovery','category':'Relief','summary':'Rebuild storm-damaged homes','currency':'USD'},
        {'id':88,'title':'School Books','category':'Education','summary':'New textbooks','currency':'USD'},
    ])
    answer=graph.run_workflow(request)
    assert answer.campaign_ids==[23,22]
    assert answer.catalogue_result_ids==[23,22]
    assert 'Semantic Relevance' in answer.agents_run
    assert 999 not in answer.campaign_ids


def test_empty_relevance_generates_conversational_recovery(install_fake_graph):
    Fake,graph=install_fake_graph
    Fake.next_intent='campaign_discovery';Fake.next_route='discovery';Fake.semantic_ids=[]
    Fake.generated_reply='I cannot find disaster relief among those published results. Is there a region you prefer?'
    req=ChatRequest(message='I want to donate search disaster areas',campaigns=[
        {'id':11,'title':'Art Fair','category':'Culture','summary':'Community gallery'}
    ])
    answer=graph.run_workflow(req)
    assert not answer.campaign_ids
    assert answer.reply != Fake.generated_reply
    assert "broaden" in answer.reply.lower()
    assert "culture" not in answer.reply.lower()
    assert 'Search Recovery' in answer.agents_run


def test_repeated_empty_replies_trigger_a_second_contextual_attempt(install_fake_graph):
    Fake,graph=install_fake_graph
    Fake.next_intent='campaign_discovery';Fake.next_route='discovery';Fake.semantic_ids=[]
    Fake.generated_reply='I could not find a matching eligible published campaign in the available catalogue. Try a different cause or location.'
    req=ChatRequest(message='I want to donate to drought relief',history=[
        {'role':'assistant','content':Fake.generated_reply}
    ])
    answer=graph.run_workflow(req)
    assert answer.reply!=Fake.generated_reply
    assert len(Fake.received)==2
    assert 'Search Recovery' in answer.agents_run


@pytest.mark.parametrize('intent', ['donation_explanation','current_world_information','popularity_comparison'])
def test_model_prompt_carries_evidence_limit(install_fake_graph,intent):
    Fake,graph=install_fake_graph
    Fake.next_intent=intent;Fake.next_route='discovery';Fake.received=[]
    Fake.generated_reply='I can explain how that works.'
    graph.run_workflow(ChatRequest(message='Can you explain that?'))
    system=Fake.received[0][0].content
    if intent=='current_world_information':assert 'live disaster-news feed' in system
    elif intent=='popularity_comparison':assert 'verified donation velocity' in system
    else:assert 'A donation amount may mean' in system


def test_secondary_published_campaign_tags_match_without_fabricated_results():
    from app.graph import search_catalogue
    records=[
        {'id':31,'title':'Community Supplies','category':'Community','location':'Kano',
         'summary':'Provide essential goods','tags':['Crisis Relief','Flood Response']},
        {'id':32,'title':'School Equipment','category':'Education','location':'Kano',
         'summary':'Classroom supplies','tags':['Education']},
    ]
    assert [c['id'] for c in search_catalogue(records,['flood'],[],'Show flood relief',20)] == [31]


def test_no_automatic_live_disaster_claims_from_empty_campaign_feed(install_fake_graph):
    Fake, graph = install_fake_graph
    Fake.next_intent='current_world_information';Fake.next_route='discovery';Fake.received=[]
    Fake.generated_reply='I cannot verify live disaster events here. I can search published Filantrophy relief campaigns.'
    result=graph.run_workflow(ChatRequest(message='Which natural disasters are happening today?',campaigns=[]))
    assert result.campaign_ids==[]
    assert result.reply != Fake.generated_reply
    assert "reliable news source" in result.reply.lower()
    assert 'Discovery' not in result.agents_run


def test_courteous_voice_fallback_rejects_unapproved_coming_soon_claim(install_fake_graph):
    Fake, graph = install_fake_graph
    Fake.next_intent = 'campaign_discovery'
    Fake.next_route = 'discovery'
    Fake.semantic_ids = []
    Fake.received = []
    Fake.generated_reply = 'A disaster campaign is coming soon!'
    result = graph.run_workflow(ChatRequest(message='Find disaster relief in Madagascar', campaigns=[
        {'id': 51, 'title': 'Gallery Exhibition', 'category': 'Culture', 'summary': 'Local artists'},
    ]))
    assert result.campaign_ids == []
    assert 'coming soon' not in result.reply.lower()
    assert 'culture' not in result.reply.lower()
    assert 'Search Recovery' in result.agents_run


def test_general_knowledge_does_not_trigger_cause_recommendations(install_fake_graph):
    Fake, graph = install_fake_graph
    Fake.next_intent = 'general_knowledge'
    Fake.next_route = 'discovery'
    Fake.received = []
    Fake.generated_reply = 'Madagascar is an island country off the southeastern coast of Africa.'
    response = graph.run_workflow(ChatRequest(message='Where is Madagascar?'))
    # v0.5.13: preserve the answer FIRST and allow one brief platform invitation.
    assert response.reply.startswith(Fake.generated_reply)
    assert 'Filantrophy' in response.reply
    assert 'Knowledge' in response.agents_run
    assert 'Discovery' not in response.agents_run


def test_social_accountability_is_knowledge_not_unrelated(install_fake_graph):
    Fake, graph = install_fake_graph
    Fake.next_intent = 'social_impact_context'
    Fake.next_route = 'out_of_scope'
    Fake.generated_reply = 'Transparency and accountability can help donors evaluate how funds are managed.'
    response = graph.run_workflow(ChatRequest(message='Why does corruption affect charitable giving?'))
    assert response.reply == Fake.generated_reply
    assert 'Knowledge' in response.agents_run
    assert 'Scope Guard' not in response.agents_run


@pytest.mark.parametrize('message', [
    'what is wrong in our environment',
    'what is currently wrong in our society and what causes should I support',
    'what is a sexual health clinic',
    'what are sex toys',
])
def test_general_and_sensitive_education_uses_knowledge_agent(install_fake_graph, message):
    Fake,graph=install_fake_graph
    Fake.next_intent='social_impact_context';Fake.next_route='discovery';Fake.received=[]
    Fake.generated_reply='Here is a useful factual explanation of the topic.'
    result=graph.run_workflow(ChatRequest(message=message))
    assert result.reply.startswith(Fake.generated_reply)
    if message == 'what are sex toys':
        assert result.reply.count('I can also help with Filantrophy') == 1
    assert 'Knowledge' in result.agents_run
    assert 'Discovery' not in result.agents_run
