# Filantrophy AI Python v0.5.4 — Integrated Sprint 2

Upgrade from v0.5.3. Keep existing environment secrets in `.env` or your deployment environment; do not commit them to source control. This release pairs with Joomla module v0.5.10.

## Delivered

- Receives up to 20 recent conversation messages and 8 explicitly consented account preferences from the authenticated Joomla server. Recent dialogue is context, **not authoritative state**.
- Uses previous turns for knowledge-agent follow-ups and recommendation context, with clearer everyday conversation prompts.
- Uses safe, deterministic data and policy guards for searches, proposals, and giving-plan action intents. Python does not execute or confirm payments or service bookings.
- Provides conservative input filtering for preferences and output hygiene for generated visitor text.
- Adds offline regression tests for preference filtering, safe context, brand wording, agent behavior and action contracts.

## Limits and required QA

The Python service is stateless by design. Durable conversation history and opt-in preferences live in Joomla and are sent with authenticated requests. **LangGraph checkpointer persistence and semantic cross-conversation retrieval are not implemented here.** Confirm session restoration on beta and check responses against real examples. Deterministic quality signals are NOT substitutes for live model response evaluations.

Run:

```sh
cd fastapi_service
python -m pytest -q
```

Expected `/health` version: `0.5.4`.
