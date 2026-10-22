# Filantrophy Python Backend 0.5.0

This release adds `app/plan_intelligence.py`, `app/multi_step.py`, `app/platform_search.py`, typed validated plan/resource contracts, and regression tests to the existing LangGraph backend.

API remains `/v1/chat` over HMAC-authenticated HTTPS. The server-owned Joomla side supplies validated published campaigns, the current ordered giving-plan draft, and public event resources. Python **proposes** draft actions; the Joomla frontend applies them. Financial operations are never performed by the LLM.

To upgrade, redeploy the FastAPI project preserving `.env` and `FILANTROPHY_SHARED_SECRET`. Install the **matching Joomla AI module v0.5.0**, because older modules do not transmit the active plan or accept the new action contracts. Do not change the Campaigns module or checkout handlers as part of this update.

Local regression suite: `python -m pip install pytest httpx && python -m pytest -q` from `fastapi_service/`.

Known limitations: only the configured public campaign feed (at most 30 entries) is searchable; real volunteer and service-provider adapters require their owning component APIs; account conversation state lives in Joomla MySQL rather than a LangGraph PostgreSQL checkpointer. Payment testing must be completed on a gateway sandbox before production.
