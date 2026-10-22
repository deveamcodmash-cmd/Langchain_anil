# Filantrophy Python LangGraph v0.5.12 — Answer-First Intelligence

Upgrade of v0.5.11, intended for Joomla module v0.5.21.

- General questions about entertainment, relationships, non-graphic adult sexual health, animal care and other clear off-platform topics route directly to Knowledge rather than service/campaign search or an extra LLM supervisor call.
- The Knowledge Agent must answer the actual question before a brief Filantrophy reminder; the reminder is shown once per unrelated topic thread, not after each response.
- Familiar scope deflections ("I can help with Filantrophy") can trigger a focused knowledge retry rather than overriding the question.
- Upstream AI provider HTTP 429 is normalized to safe `429 {"detail":"The AI model is temporarily rate limited"}`. Raw upstream errors and secrets are not exposed.
- One provider call is used for recognized general topics when the initial knowledge answer is useful. Actual model calls, retries and provider availability require live verification.
- No change to payment processing, donation authorization or booking execution.

Test: `cd fastapi_service && PYTHONPATH=. pytest -q`.
Set `OPENAI_API_KEY`, `OPENAI_MODEL` and `FILANTROPHY_SHARED_SECRET` in the existing private `.env`, restart Uvicorn and verify `/health` reports `0.5.12`.
