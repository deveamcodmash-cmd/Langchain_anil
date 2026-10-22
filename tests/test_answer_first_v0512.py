"""v0.5.12 acceptance: answer first, one brand pivot, provider limit diagnosis."""
import json
import time
import uuid

import pytest
from app.dialogue_intelligence import general_only_question, off_topic_reminder, generic_nonanswer
from app.schemas import ChatRequest, ConversationMessage, PlatformResource
from app.service_intelligence import is_service_request
from app.graph import run_workflow

SERVICES = [PlatformResource(id=12, title='Education Support Program', kind='service', summary='School support')]

@pytest.mark.parametrize('message', [
    'recommend me best time to have sex',
    'what is the best time for intimacy?',
    'provide me best movie list',
    'who is Taylor Swift?',
    'recommend dog breeding techniques',
])
def test_general_question_cannot_become_service_search(message):
    assert general_only_question(message)
    assert not is_service_request(message, SERVICES)

@pytest.mark.parametrize('message', [
    'Find sexual health services on Filantrophy',
    'Is there any services with sex',
    'Show me charity campaigns about sexual health',
])
def test_platform_explicit_beats_general_keyword(message):
    assert not general_only_question(message)


def test_knowledge_first_then_one_platform_pivot():
    question='recommend me best time to have sex'
    answer='There is no single best time; the important factors are mutual consent, comfort, privacy, and when both people feel ready.'
    first=off_topic_reminder(ChatRequest(message=question),answer)
    assert first.startswith(answer)
    assert first.count('I can also help')==1
    assert 'health and well-being' in first
    history=[ConversationMessage(role='user',content=question), ConversationMessage(role='assistant',content=first)]
    follow=off_topic_reminder(ChatRequest(message='What about mornings?',history=history), 'A morning time can be fine if you both prefer it.')
    assert 'Filantrophy' not in follow
    follow2=off_topic_reminder(ChatRequest(message='what about sex in the morning?',history=history),'A morning time can be fine if you both prefer it.')
    assert 'I can also help' not in follow2


def test_generic_promotion_is_not_a_real_answer():
    assert generic_nonanswer('I can help with Filantrophy campaigns and giving plans. What cause matters to you?')
    assert generic_nonanswer('I am here to help with Filantrophy campaigns.')
    assert not generic_nonanswer('There is no universal best time for intimacy. Consent and comfort matter.')


def test_general_prompt_skip_supervisor(install_fake_graph_for_answer_first):
    Fake,graph=install_fake_graph_for_answer_first
    Fake.received=[]
    Fake.generated_reply='There is no universally best time; choose one when both partners feel relaxed, willing and comfortable.'
    response=graph.run_workflow(ChatRequest(message='recommend me best time to have sex', resources=SERVICES))
    assert response.reply.startswith(Fake.generated_reply)
    assert response.reply.count('I can also help')==1
    assert response.campaign_ids==[]
    assert response.agents_run==['General Knowledge Router','Knowledge']
    assert len(Fake.received)==1  # one knowledge call, no paid supervisor hop


@pytest.fixture
def install_fake_graph_for_answer_first(monkeypatch):
    import sys,types
    class FakeGraph:
        def __init__(self,*_):self.nodes={};self.edges={};self.branches={};self.entry=None
        def add_node(self,n,f):self.nodes[n]=f
        def add_edge(self,n,target):self.edges[n]=target
        def add_conditional_edges(self,n,f,mapping):self.branches[n]=(f,mapping)
        def set_entry_point(self,n):self.entry=n
        def compile(self):return self
        def invoke(self,state,config=None):
            node=self.entry
            for _ in range(10):
                if node=='__END__':return state
                state.update(self.nodes[node](state))
                if node in self.branches:
                    f,targets=self.branches[node];node=targets[f(state)]
                else:node=self.edges[node]
            raise AssertionError('Graph loop')
    class FakeMessage:
        def __init__(self,content):self.content=content
    class FakeModel:
        received=[]
        generated_reply='There is no single best time for intimacy.'
        def __init__(self,*a,**kw):pass
        def with_structured_output(self,schema):
            class FakeSchema:
                def invoke(self, messages):
                    if schema.__name__=='Decision':
                        raise AssertionError('Known general questions must skip structured supervisor')
                    return schema(matching_ids=[])
            return FakeSchema()
        def invoke(self,messages):
            FakeModel.received.append(messages)
            return types.SimpleNamespace(content=FakeModel.generated_reply)
    langgraph=types.ModuleType('langgraph.graph');langgraph.StateGraph=FakeGraph;langgraph.END='__END__'
    messages=types.ModuleType('langchain_core.messages');messages.SystemMessage=FakeMessage;messages.HumanMessage=FakeMessage;messages.AIMessage=FakeMessage
    monkeypatch.setitem(sys.modules,'langgraph',types.ModuleType('langgraph'))
    monkeypatch.setitem(sys.modules,'langgraph.graph',langgraph)
    monkeypatch.setitem(sys.modules,'langchain_core',types.ModuleType('langchain_core'))
    monkeypatch.setitem(sys.modules,'langchain_core.messages',messages)
    monkeypatch.setitem(sys.modules,'langchain_openai',types.SimpleNamespace(ChatOpenAI=FakeModel))
    monkeypatch.setenv('OPENAI_API_KEY','testing-fake-no-secret')
    from app import graph
    monkeypatch.setattr(graph,'_GRAPH',None)
    yield FakeModel,graph
    graph._GRAPH=None


def test_upstream_429_returns_sanitized_rate_error(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app import graph
    from tests.test_api import signature
    class RateLimitError(Exception):
        status_code=429
    def raised(_):
        raise RateLimitError('sensitive-provider-detail-not-to-echo')
    monkeypatch.setattr(graph,'run_workflow',raised)
    payload=json.dumps({'message':'explain this question'}).encode()
    result=TestClient(app).post('/v1/chat',content=payload,headers=signature(payload,uuid.uuid4().hex,str(int(time.time()))))
    assert result.status_code==429
    assert result.json()['detail']=='The AI model is temporarily rate limited'
    assert 'sensitive-provider-detail' not in result.text
