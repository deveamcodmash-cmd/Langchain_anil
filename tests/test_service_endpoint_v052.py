"""HMAC authenticated end-to-end service search; no OpenAI needed."""
import hashlib
import hmac
import json
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app


def test_signed_chat_search_physio(monkeypatch):
    secret='only-for-local-test-shared-secret-at-least-32'
    monkeypatch.setenv('FILANTROPHY_SHARED_SECRET', secret)
    payload={'message':'show me Physiotherapy Session','resources':[
        {'id':85,'title':'Physiotherapy Session','kind':'service',
         'summary':'MASSAGE THERAPY · Serenity Wellness Centre','location':'Abuja'}
    ]}
    body=json.dumps(payload,separators=(',',':')).encode()
    ts=str(int(time.time()))
    nonce=uuid4().hex
    signature=hmac.new(secret.encode(), ts.encode()+b'.'+nonce.encode()+b'.'+body, hashlib.sha256).hexdigest()
    headers={'X-Filantrophy-Timestamp':ts,'X-Filantrophy-Nonce':nonce,'X-Filantrophy-Signature':'sha256='+signature}
    response=TestClient(app).post('/v1/chat',content=body,headers=headers)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['mode']=='platform_search'
    assert [row['id'] for row in result['resources']]==[85]
    assert result['resource_result_ids']==[85]
    assert not result.get('campaign_ids')
