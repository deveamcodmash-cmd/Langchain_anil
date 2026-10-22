"""Joomla-to-Python API. No checkout/payment endpoints by design."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .schemas import ChatRequest
from .policy import CapabilityRequest, PolicyCheckRequest
from .capabilities import list_capabilities, policy_decision
from .security import authenticate

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('filantrophy-ai')
app=FastAPI(title='Filantrophy LangGraph API',version='0.5.21', docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/health')
async def public_health():
    # Public uptime endpoint; never prints credentials, user data, or configuration.
    return {'status':'ok','service':'filantrophy-langgraph','version':'0.5.21'}


@app.post('/v1/health')
async def private_health(request: Request):
    body=await request.body()
    if len(body)>8192:
        raise HTTPException(status_code=413,detail='Request too large')
    authenticate(body,request)
    return {'status':'ok','service':'filantrophy-langgraph','openai_configured':bool(os.getenv('OPENAI_API_KEY')) and not os.getenv('OPENAI_API_KEY', '').startswith('PASTE_'), 'graph':'Scope Guard → Supervisor → Specialist Agents', 'capability_catalogue_version':'0.4.0'}


@app.post('/v1/chat')
async def chat(request: Request):
    body=await request.body()
    if len(body)>80000:
        raise HTTPException(status_code=413,detail='Request too large')
    authenticate(body,request)
    try:
        parsed=ChatRequest.model_validate_json(body)
    except ValidationError as exc:
        # Observability without values, prompts, emails or unknown field names.
        # This distinguishes contract mismatches from tunnel or API-key issues.
        safe_roots={'ranking_context','ranking_data','message','history',
                    'memory','campaigns','resources','current_plan',
                    'booking_context','account_context','client_timezone',
                    'site_facts','recent_campaign_ids'}
        reasons=[]
        for issue in exc.errors()[:6]:
            loc=issue.get('loc',())
            root=str(loc[0]) if loc else 'unknown'
            reasons.append((root if root in safe_roots else 'unknown')+':'+str(issue.get('type','invalid')))
        logger.warning('Signed chat schema validation failed: %s',','.join(reasons))
        raise HTTPException(status_code=422,detail='Invalid chat request') from None
    try:
        from .graph import run_workflow
        response=run_workflow(parsed)
        from .graph import normalize_public_reply
        from .dialogue_intelligence import general_only_question
        result=response.model_dump()
        # Privacy-safe operational metric: log route labels, never chat text.
        route=response.mode if response.mode.replace('_','').isalnum() and len(response.mode)<=40 else 'other'
        logger.info('AI chat completed mode=%s', route)
        result["reply"]=normalize_public_reply(result.get("reply") or "", preserve_generic_noun=general_only_question(parsed.message))
        return result
    except (ImportError,ModuleNotFoundError):
        logger.exception('AI dependencies unavailable')
        raise HTTPException(status_code=503,detail='Python AI dependencies have not been installed')
    except RuntimeError as exc:
        logger.warning('AI configuration error')
        raise HTTPException(status_code=503,detail='Python AI model is not configured') from exc
    except Exception as exc:
        # A provider 429 is temporary capacity pressure, not a malformed user
        # question. Never leak provider response bodies, keys or prompt text.
        status=getattr(exc,'status_code',None)
        if status==429 or type(exc).__name__ in {'RateLimitError','TooManyRequestsError'}:
            logger.warning('Agent workflow rate limited upstream')
            raise HTTPException(status_code=429,detail='The AI model is temporarily rate limited') from None
        # No provider exception text or stack: those can embed user messages.
        logger.warning('Agent workflow failed: %s', type(exc).__name__)
        raise HTTPException(status_code=502,detail='The agent workflow is temporarily unavailable')


@app.post('/v1/capabilities')
async def capabilities(request: Request):
    """Signed, read-only capability map for the authenticated Joomla actor.

    The actor role MUST come from trusted Joomla server-side ACL lookup. This
    informational endpoint is not a permission to execute an operation.
    """
    body=await request.body()
    if len(body)>8192:
        raise HTTPException(status_code=413, detail='Request too large')
    authenticate(body,request)
    try:
        parsed=CapabilityRequest.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=422, detail='Invalid capability request')
    records=list_capabilities(parsed.actor_role,parsed.area)
    return {'version':'0.5.21','actor_role':parsed.actor_role, 'capabilities':records,
            'notice':'Capability visibility is informational. All mutations require authoritative platform authorization.'}


@app.post('/v1/policy-check')
async def policy_check(request: Request):
    """Signed diagnostic policy preview. Cannot execute any platform action."""
    body=await request.body()
    if len(body)>8192:
        raise HTTPException(status_code=413, detail='Request too large')
    authenticate(body,request)
    try:
        parsed=PolicyCheckRequest.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=422, detail='Invalid policy request')
    return policy_decision(parsed.capability_key,parsed.actor_role,
                           consent=parsed.explicit_approval)
