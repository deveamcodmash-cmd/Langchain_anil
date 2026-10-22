"""HTTP 422 regression: Joomla 0.5.24 extra ranking filter marker.

The public API remains strict for unknown keys and respects filtered-ranking
privacy. Only the known old Joomla marker is backwards compatible.
"""
import hashlib
import hmac
import json
import os
import time
import uuid

from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.schemas import ChatRequest, ChatResponse
from app.graph import run_workflow

_SECRET = 'a-private-transport-test-secret-longer-than-thirty-two'


def _signed(payload):
    os.environ['FILANTROPHY_SHARED_SECRET'] = _SECRET
    body = json.dumps(payload, separators=(',', ':')).encode()
    stamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    digest = hmac.new(_SECRET.encode(), stamp.encode()+b'.'+nonce.encode()+b'.'+body, hashlib.sha256).hexdigest()
    headers = {
        'X-Filantrophy-Timestamp':stamp,
        'X-Filantrophy-Nonce':nonce,
        'X-Filantrophy-Signature':'sha256='+digest,
        'Content-Type':'application/json',
    }
    return TestClient(app).post('/v1/chat',content=body,headers=headers)


def test_old_joomla_ranking_request_is_accepted_and_kept_unpublished():
    # This matches the exact extra field that Joomla v0.5.24 sent, which
    # previously made FastAPI return 422 for even an unfiltered Top 10.
    payload={'message':'Show me the top 10 corporate donors',
             'ranking_context':{'type':'corporate','period':'all_time','count':10,'unsupported_filter':False},
             'ranking_data':{'status':'not_published','type':'corporate','period':'all_time','rows':[],
                             'verified':False,'total':0,'last_updated':None,
                             'message':'Verified corporate rankings are pending.'}}
    result=_signed(payload)
    assert result.status_code == 200,result.text
    response=result.json()
    assert response['mode']=='ranking_pending'
    assert response['campaign_ids']==[]


def test_filtered_old_joomla_request_cannot_publish_global_rankings():
    payload={'message':'show top 10 service providers in Nigeria',
             'ranking_context':{'type':'providers','count':10,'period':'all_time','unsupported_filter':True},
             'ranking_data':{'status':'published','type':'providers','period':'all_time','verified':True,
                             'total':1,'rows':[{'rank':1,'title':'Public Test Provider','score':100,'category':'Wellness'}]}}
    response=_signed(payload)
    assert response.status_code == 200,response.text
    data=response.json()
    assert data['mode']=='ranking_pending'
    assert 'Public Test Provider' not in data['reply']
    assert data['campaign_ids']==[]


def test_new_joomla_context_only_has_public_contract_keys():
    req=ChatRequest.model_validate({'message':'Show top five donors',
                                   'ranking_context':{'type':'individual','period':'year','count':5}})
    assert req.ranking_context.type=='individual'
    assert req.ranking_context.unsupported_filter is False


def test_unknown_ranking_context_keys_are_still_forbidden():
    from pytest import raises
    with raises(ValidationError):
        ChatRequest.model_validate({'message':'Show donors','ranking_context':{
            'type':'individual','period':'year','count':5,'email':'private@invalid.test'}})
