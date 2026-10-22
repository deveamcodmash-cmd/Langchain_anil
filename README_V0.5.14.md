# Filantrophy Python LangGraph v0.5.14 — Site Intelligence

Paired with **Joomla AI Module v0.5.23**; built directly from your v0.5.13/v0.5.22 uploads.

## Changes

- Adds a reviewed **site knowledge context** from the Joomla module's `knowledge/site-guide.json`. Joomla selects relevant facts per visitor question; they are passed inside the already signed server-to-server chat request. These are *site documentation*, not instructions from visitor messages or model output.
- Adds a deterministic read-only **Role Guide** for comparisons of Individual, Corporate, Service Provider and Event Organiser users. It answers from the shipped handbook before the service directory can mistake `service providers` for a booking search. The Joomla Direct AI configuration also uses this same source, with a model-free role help fallback.
- Improves service intent routing: education/account comparisons and instructional help do not call the service search; explicit `show/find/book` requests still use verified published listings.
- The Knowledge Agent gets selected website facts for other platform explanatory questions and cannot treat these notes as proof of a finished action. Existing protected donation and booking executors are unchanged.
- The packed handbook covers site overview, account roles, giving, campaign creation, verification, booking/coupons, volunteering, event participation, directories, dashboards, receipts and privacy.

## Site Knowledge Ownership

`modules/mod_filantrophy_ai/knowledge/site-guide.json` is the handbook's source of truth. A site administrator should review and approve its content, particularly feature availability, onboarding flows and restrictions. It is not scraped from the live website and not a vector database. For newly published features or changed account permissions, update these approved facts (and retain them in the next release). Never put secrets, customer PII or private menu URLs in public knowledge.

## Deployment And QA

1. Back up both current installations and the Python `.env`.
2. Deploy Python v0.5.14 and restart FastAPI; check `GET /health` for `0.5.14`.
3. Upgrade the Joomla module to v0.5.23 through the extension installer; keep Python/LangGraph mode selected.
4. Clear cache and test a real role comparison, service search, campaign wizard help, and account impact permissions.
5. Run `PYTHONPATH=. pytest -q` from `fastapi_service` and review `evaluation/site_intelligence_v0514.jsonl` with live model and real site data.

**Boundaries:** No dynamic crawl of all pages, no DB permission change, no automatic provider or campaign registration, and no undocumented URL generation. A longer-term CMS indexing and administration workflow can extend the handbook safely after its source and ACL rules are approved.
