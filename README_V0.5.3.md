# Filantrophy AI LangGraph v0.5.3

**Upgrades:** v0.5.2 → v0.5.3. Deploy with `mod_filantrophy_ai` v0.5.9.

## Scope — Integration Sprint 1

- **Conversation continuity:** Accepts up to 20 bounded prior user/assistant messages from the existing authenticated Joomla conversation store instead of 8. Prior turns are conversational context, not authorization or proof.
- **Knowledge agent:** Receives recent conversation turns and can resolve a limited class of elliptical follow-ups (e.g. “How does that work?”) against the previous **user** topic when choosing reviewed Filantrophy facts. It does not treat assistant claims as evidence.
- **Recommendation agent:** Receives relevant recent turns as context while all actual recommendations remain limited to the server-supplied published catalogue.
- **Conversational style:** Shared language instructions request concise, polite, natural sentence-case answers; at most one essential clarification; no invented completed actions or promises.
- **Grounded capabilities:** Reviewed service-booking description reflects the actual **Book Now** UI, and explicitly distinguishes a booking draft from verified native booking confirmation. Event/volunteer actions are still not executable by the Python agent.
- **Privacy:** Previous history containing detected sensitive payment data is withheld from graph context; the incoming message remains protected by the existing payment-data guard.
- **Truthful giving-plan drafts:** Human-readable names and amounts are used in proposed plans while the verified ID-based proposal remains authoritative to the frontend.

No new payment, checkout, booking mutation, credentials or database tables are introduced in the Python package. This is not a durable semantic vector memory or universal tool executor; those require a separately reviewed, role-aware design.

## Deployment

1. Back up FastAPI v0.5.2 and `.env`. Do not overwrite your existing `.env` with `.env.example`.
2. Deploy the full archive over the same FastAPI directory; remove obsolete files only if you have verified they are not custom extensions.
3. Activate your existing Python environment and install/update dependencies from `requirements.txt` if required.
4. Restart Uvicorn; use `/health` to confirm version **0.5.3**.
5. Install matching Joomla AI module **v0.5.9**; clear Joomla and browser caches.
6. Never expose the signed `/v1/chat` endpoint directly to the browser.

## Offline regression

Run `python -m pytest -q tests` from `fastapi_service`. The release was packaged after 101 regression tests passed locally; live model/Cloudflare/Joomla testing remains required.
