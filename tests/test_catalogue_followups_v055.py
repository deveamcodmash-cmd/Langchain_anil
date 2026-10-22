"""Regression cases for chat pagination and natural-language service search."""
from __future__ import annotations

import sys
import types

from app.graph import search_catalogue
from app.platform_search import resource_search
from app.schemas import ChatRequest, PlatformResource


def test_services_on_filantrophy_ignore_brand_and_filler():
    req=ChatRequest(message='yes give me yoga services available in Filantrophy', resources=[
        PlatformResource(id=85,title='Yoga & Meditation Session',kind='service',summary='Serenity Wellness Centre yoga and meditation',location='Abuja'),
        PlatformResource(id=86,title='Dental Checkup',kind='service',summary='Healthy smiles',location='Lagos'),
    ])
    result=resource_search(req)
    assert result is not None
    assert [r.id for r in result.resources] == [85]


def test_generic_service_search_does_not_require_matching_generic_words():
    req=ChatRequest(message='show me services available on Filantrophy', resources=[
        PlatformResource(id=85,title='Yoga & Meditation Session',kind='service',summary='Wellness',location='Abuja'),
        PlatformResource(id=86,title='Dental Checkup',kind='service',summary='Healthcare',location='Lagos'),
    ])
    result=resource_search(req)
    assert result is not None
    assert [r.id for r in result.resources] == [85,86]


def test_search_catalogue_only_returns_relevant_campaigns():
    campaigns=[{'id':i,'title':f'Campaign {i}', 'category':'Healthcare' if i<5 else 'Education',
                'location':'Abuja','summary':'Health services' if i<5 else 'School supplies'} for i in range(1,9)]
    rows=search_catalogue(campaigns,['healthcare'],[],'show me 3 healthcare campaigns',limit=30)
    assert [x['id'] for x in rows]==[1,2,3,4]


def test_graph_gives_first_batch_and_full_ranked_cursor(monkeypatch):
    # No network/model calls: exercise the actual LangGraph graph with a fake
    # decision model to catch lost full-ranked IDs in the response contract.
    from app import graph
    from app.graph import Decision

    class FakeRouter:
        def invoke(self, messages):
            return Decision(route='discovery', cause_keywords=['healthcare'], desired_count=3)

    class FakeModel:
        def __init__(self,*args,**kwargs):pass
        def with_structured_output(self, schema):return FakeRouter()
        def invoke(self, messages):return types.SimpleNamespace(content='Here are three healthcare campaigns.')

    class FakeStateGraph:
        def __init__(self, state_type):
            self.nodes={};self.edges={};self.branch={};self.entry=None
        def add_node(self,name,fn):self.nodes[name]=fn
        def add_edge(self,name,target):self.edges[name]=target
        def add_conditional_edges(self,name,fn,mapping):self.branch[name]=(fn,mapping)
        def set_entry_point(self,name):self.entry=name
        def compile(self):return self
        def invoke(self,state,config=None):
            item=self.entry
            while item!='__END__':
                state.update(self.nodes[item](state))
                if item in self.branch:
                    fn,mapping=self.branch[item];item=mapping[fn(state)]
                else:item=self.edges[item]
            return state

    class FakeMessage:
        def __init__(self, content):self.content=content

    graph_module=types.ModuleType('langgraph.graph')
    graph_module.StateGraph=FakeStateGraph;graph_module.END='__END__'
    langgraph_module=types.ModuleType('langgraph');langgraph_module.graph=graph_module
    core_module=types.ModuleType('langchain_core')
    core_messages=types.ModuleType('langchain_core.messages')
    core_messages.SystemMessage=FakeMessage;core_messages.HumanMessage=FakeMessage;core_messages.AIMessage=FakeMessage
    monkeypatch.setitem(sys.modules,'langgraph',langgraph_module)
    monkeypatch.setitem(sys.modules,'langgraph.graph',graph_module)
    monkeypatch.setitem(sys.modules,'langchain_core',core_module)
    monkeypatch.setitem(sys.modules,'langchain_core.messages',core_messages)
    monkeypatch.setenv('OPENAI_API_KEY','unit-test-only-key')
    monkeypatch.setitem(sys.modules,'langchain_openai',types.SimpleNamespace(ChatOpenAI=FakeModel))
    monkeypatch.setattr(graph,'_GRAPH',None)
    req=ChatRequest(message='Show me three healthcare campaigns',campaigns=[
        {'id':i,'title':f'Healthcare {i}', 'category':'Healthcare', 'currency':'USD',
         'location':'Abuja','summary':'Care'} for i in range(1,9)
    ])
    result=graph.run_workflow(req)
    assert result.campaign_ids==[1,2,3]
    assert result.catalogue_result_ids==list(range(1,9))
    graph._GRAPH=None
