# Filantrophy AI Python v0.5.13 — General Intelligence Routing

**Matched Joomla module:** v0.5.22. Upgrade from Python v0.5.12 / Joomla v0.5.21.

## Changes

- Unknown everyday subjects now take an answer-first Knowledge Agent route. The routing guard is **based on explicit platform intent**, not an expanding list of popular topic keywords.
- The model interprets imperfect language and implicit meaning, answers concisely and never infers a reliable current-world ranking from memory alone.
- General questions **do not receive platform-only retrieval instructions**. Missing Filantrophy policy facts cannot force a scope disclaimer for ordinary questions.
- A generic Filantrophy-only deflection triggers a focused retry; a second deflection yields an honest bounded clarification rather than another sales pitch.
- A short Filantrophy invitation is appended only *after* an actual general answer, suppressed for immediate follow-ups so the dialogue does not loop or advertise every turn.
- Ordinary dictionary uses of “philanthropy” remain unmodified; the official platform brand still displays as Filantrophy in platform replies.
- Existing verified campaign, service, event, booking-form and giving-plan tools still take precedence for supported platform actions.

## Important limits

This release does **not** add live web retrieval, current-world statistics, or unrestricted platform actions. For current rankings, news, and statistics the model must identify uncertain evidence rather than invent a latest fact. Model fluency and factual correctness require live evaluation with the configured model; local tests validate routes and action boundaries only.

## Deployment

1. Back up your currently deployed `fastapi_service` and private `.env`.
2. Extract this Python ZIP into the application root, keeping `.env` secure and unchanged.
3. Install dependencies using the existing `requirements.txt` in your virtual environment.
4. Restart Uvicorn / deployment process and confirm `/health` returns `version: 0.5.13`.
5. Upgrade the matched Joomla module to v0.5.22 and clear all caches.
6. Use **Python FastAPI / LangGraph Multi-Agent** as the Joomla AI Processing Engine for the improved routing.

## QA

Run `PYTHONPATH=. pytest -q` from `fastapi_service/` and use `evaluation/general_answer_first_v0513.jsonl` to evaluate live model responses with explicit source verification.

Payments, reservations and giving-plan saving remain under the existing backend's authorization and confirmation controls.
