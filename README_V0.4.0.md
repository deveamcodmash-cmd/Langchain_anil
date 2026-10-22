# Filantrophy AI FastAPI v0.4.0 — Platform Foundation

This is an incremental upgrade from the existing 0.3.0 FastAPI service. It does not change Joomla payment processing, OpenAI settings or shared-secret authentication.

## Install / Upgrade

1. Back up the existing service and keep its `.env` private.
2. Extract this ZIP and move updated `fastapi_service/` files into the deployed service.
3. Install or update dependencies using `pip install -r requirements.txt`.
4. Restart FastAPI (or redeploy Render).
5. Test `GET /health` → `version: 0.4.0`.
6. In Joomla, keep the current AI Module v0.3.0 and existing tunnel URL and shared secret.

## New Signed Endpoints

- `POST /v1/capabilities` — request `{"actor_role":"individual","area":"giving"}`. Returns a role-filterable capability catalogue, not permission to execute.
- `POST /v1/policy-check` — request `{"actor_role":"guest","capability_key":"admin.operations","explicit_approval":false}`. Returns deny reason; no backend record is touched.

Both endpoints use **exactly the same HMAC request headers** as `/v1/chat`. The actor role must be resolved by Filantrophy's authenticated server, not supplied unchecked by a browser.

## Tests

```bash
cd fastapi_service
python -m pytest -q
python tools/evaluate_platform.py
```

LLM-based live responses require the packages and private OpenAI settings already used by v0.3.0. Offline tests do not call OpenAI. This foundation does not include verified end-to-end Joomla-to-FastAPI or payment tests.

## What Changed

- Capability registry and conservative role-policy preview.
- Starter source-backed platform knowledge instead of stale payment-provider wording in the Knowledge Agent.
- Broader Filantrophy scope recognition.
- Guardrails for unimplemented event/volunteer/service/admin write operations.
- Early blocking of likely payment-card numbers and access credentials in chat.
- Typed draft/search contracts for future platform APIs.
- Offline labelled evaluation dataset and runner.

## Non-Goals

No cross-platform write APIs, payment initiations, RAG indexing, fine-tuning, persistent LangGraph checkpoints, or admin changes have been enabled in v0.4.0.
