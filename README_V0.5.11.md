# Filantrophy AI Python v0.5.11 — All-Four-Phase Dialogue Improvement

**Base:** v0.5.10. **Paired Joomla package:** `mod_filantrophy_ai` v0.5.20.

This release coordinates four areas of improvement without changing the financial or booking execution authority.

## Phase 1 — Intent And Topic Intelligence

- Ordinary factual, media, music, hobby, animal-care and educational questions are routed to general knowledge instead of being refused by the scope gate.
- Explicit entertainment, movies and sex-education requests are no longer misrouted to service search merely because their words overlap a published listing.
- The model's Knowledge Agent is instructed to answer briefly first; the Filantrophy reminder is shown once per recent unrelated thread, rather than after every message.
- A single bounded retry is available when the model responds with generic Filantrophy advertising instead of addressing the question. Content safety restrictions are unchanged.

## Phase 2 — Conversation State And Follow-Up

- A positive reply is interpreted against the **most recent explicit assistant offer**, then grounded against the current signed Joomla catalogue.
- Elliptical offers such as “show some of those campaigns” use the preceding user subject to recover the intended cause.
- When an accepted offer finds no published result, the answer closes the loop instead of asking the same question again.
- A constrained structured-output interpreter can resolve other unfamiliar accepted search offers without fabricating results or authorizing mutations.
- Account-scoped Joomla conversation synchronization and existing plan transaction guards are retained. Full durable LangGraph checkpoint storage is **not** introduced in this release.

## Phase 3 — Platform Guidance And Verified Actions

- Campaign-creation guidance follows the known fundraising wizard: title, cause, goal/currency/start, beneficiary, location, summary/story, cover, payment readiness, and milestones for projects.
- “Top charity” returns only publicly reported campaign funding totals, grouped by currency, from the provided **partial published snapshot**; it never claims a global all-time winner without data.
- Booking-form help is based on a limited active booking hint (published service ID + form stage) verified against the Joomla public service catalogue. No contact details, card data, selected appointment, coupon, or account credentials are passed through that hint.
- The current time can be answered using the browser's reported IANA timezone (falls back to UTC); it does not reveal or request geolocation.
- No new write permissions, automatic bookings, payments, or account modifications are enabled by this release.

## Phase 4 — Evaluation, Response Quality And Diagnostics

- Expanded offline suite: **263 passing Python tests** at release build time, including new screenshot-derived routing, follow-up and data-grounding contracts.
- `PYTHONPATH=. python tools/evaluate_dialogue_v0511.py` runs 11 deterministic scenario checks without a model or network.
- Browser test coverage confirms five-at-a-time pagination, launcher/composer controls, minimal cards, and booking-context transmission without private form fields.
- AI workflow failures are logged by exception class only, not user messages or upstream provider exception payloads.
- **Live model behavior, factual accuracy, site-specific access/ACLs and real booking flows are not validated by offline tests.** Run acceptance checks against beta with real published data and actual model credentials.

## Upgrade

1. Back up current v0.5.10 source and `.env`.
2. Deploy the Python ZIP, preserving the current `.env`, host environment and Python dependencies.
3. Restart service. Confirm `GET /health` reports version `0.5.11`.
4. Upgrade Joomla AI Module to v0.5.20 without uninstalling.
5. Set the module's processing engine to **Python / LangGraph**; the Direct AI fallback has different routing logic.
6. Clear Joomla/browser/CDN caches and run QA conversation scenarios.

No database migration is added; database saves and payment flows are unchanged.
