# Filantrophy AI Python v0.5.5 — Intent & Recovery Upgrade

Pairs with Joomla AI module **v0.5.11**. Upgrade in place from Python v0.5.4. Keep `.env` and credentials on the trusted Python host; no new secrets are required.

## Changes

- Structured semantic `intent` separate from graph `route`. Campaign discovery, donation explanations, live/current disaster questions, popularity queries, giving-plan requests, and platform questions use distinct behaviors.
- `normalize_decision()` prevents a discovery route from swallowing informational intents if the model's route and semantic intent disagree.
- Catalogue retrieval includes *verified published public tags* supplied by Joomla, not model-created metadata.
- Semantic relevance judge runs when lexical results are sparse or the request has specific topics/locations. Model outputs only IDs, and Python/Joomla validate every ID against the supplied, eligible published catalogue.
- The old unconditional no-results sentence is removed. No-match recovery generates a contextual answer without inventing campaigns; repetitive previous replies are detected and regenerated once.
- Duplicate assistant failures are compacted out of model context while retaining the full Joomla conversation history.
- The knowledge agent uses explicit evidence-bound prompts for current disaster news, campaign popularity metrics, and donation amounts. There is **no live disaster news integration** and **no authoritative trending-donation feed**, so current/trending facts cannot be confirmed.
- 60 example prompts in `evaluation/intelligence_cases.jsonl` plus an opt-in read-only real-model evaluation runner `tools/evaluate_live_intelligence.py`.

## Run Tests

```bash
cd fastapi_service
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

To test with a real configured model (optional; incurs API usage):

```bash
python tools/evaluate_live_intelligence.py --limit 10 --out intelligence_live_results.json
```

The runner tests agent routing using public demo records. Human review of returned responses and testing against actual beta catalogue remain required. It does NOT execute payments, bookings, or Joomla updates.

## Explicit Limits

- Python remains stateless. Durable conversation history and opt-in preferences remain on the Joomla side; this does **not** introduce a LangGraph checkpointer or cross-conversation vector memory.
- Campaign discovery is limited to the signed, eligible catalogue snapshot Joomla sends (typically up to 30 latest/featured campaigns). It cannot search all website campaigns, nor live world events, unless new trusted indexing/feed capabilities are added later.
- Semantic relevance remains an LLM judgment and can be wrong. Server-side ID verification prevents invented *records*, not all relevance mistakes. Evaluate on beta and refine.
- Giving-plan action proposals, booking and payment safeguards remain unchanged. No monetary action is executed by LangGraph.

`GET /health` must report `0.5.5` after redeployment.
