# Filantrophy AI Python v0.5.6 — Natural Response Intelligence

**Matched Joomla AI Module:** v0.5.12. Builds on Python v0.5.5 / Joomla v0.5.11.

## Response Improvements

- `app/conversation_voice.py` adds a consistent, inclusive visitor response policy, grounded alternatives and deterministic quality signals.
- The LangGraph Knowledge and Recommendation agents now answer the current intent first, use relevant context, and avoid repetitive stock openings.
- A bounded **single style revision** is attempted for unhelpful or misleading narrative replies. No style model may execute financial, booking, account or publishing actions.
- Missing campaign searches can suggest only related categories confirmed in the supplied public Joomla catalogue, or offer to broaden the search. Unrelated campaigns are not misrepresented as substitutes.
- General established facts and social-impact context can be answered by the Knowledge Agent. Current events and rankings are still treated as unverified without an authoritative feed.
- No specific campaign, feature or category may be promised as **Coming Soon** without an approved, machine-readable roadmap status (none is supplied in this release).
- Service, event, volunteering and unsupported-action copy now uses a direct, helpful style while keeping permission boundaries intact.
- `evaluation/response_voice_cases.jsonl` includes 24 natural-response review cases; the existing live runner now captures heuristic tone flags and excerpts for manual review.

## Security & Evidence

The update does **not** allow the model to confirm payments, create bookings, invent availability, change account data, infer sensitive personal details, issue verified rankings or alter published campaigns. Joomla remains the authority for public records and actions. Do not call a campaign "verified impact" based solely on publishing status.

## Deploy

1. Back up the Python service and Joomla module. Keep your existing `.env`/HMAC secret separate.
2. Replace Python source with v0.5.6, install dependencies from requirements.txt, then restart Uvicorn / Render.
3. Check `/health` reports `0.5.6`; test the signed `/v1/chat` endpoint.
4. Upgrade the Joomla module to **v0.5.12**, clear Joomla/CDN/browser caches.
5. Run both ordinary and failure-case conversations; compare output against the QA guide.

## Local tests

```sh
cd fastapi_service
PYTHONPATH=. python -m pytest -q
```

**Limits:** Offline Python mocks cannot establish live model politeness, factuality or overall user satisfaction. Prompt injections in user content and campaign descriptions remain untrusted. The live review runner requires a configured key on the **trusted Python host** and should be assessed by a human before rollout. There is no live-news source, verified trending-ranking feed or approved roadmap metadata in this package.
