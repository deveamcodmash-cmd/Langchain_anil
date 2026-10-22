# Filantrophy AI v0.5.9 — Contextual Giving Plan Actions

Paired with Joomla AI Module v0.5.15.

## Why
Previously, "decrease the total budget to 9000" could bypass the plan-action route. A later reply such as "yes" or "USD" could then start a new campaign recommendation instead of modifying the verified current draft.

## What changed
- Explicit budget targets recognise `decrease/reduce/lower/cut/raise` followed by `to` as **set total**, not an adjustment by that amount.
- Bare currency or affirmation replies resolve a **recent outstanding plan clarification** against the current validated giving plan. Unrelated and already-completed turns cannot replay prior actions.
- Unfamiliar plan-edit phrasing may use a bounded structured LangChain classifier. It cannot create a payment, choose campaign IDs, or select amounts not written in the latest user message. Its proposed action still travels through Joomla's allowlist, draft guard, and browser executor.
- Requests for different campaigns/plans, informational questions, unsupported currency conversion, and ungrounded ordinal positions cannot silently modify the existing plan.
- The Python API has no write access to donor payment records; success must be reported by the frontend after actual draft mutation.

## Offline tests
From `fastapi_service`:

```bash
PYTHONPATH=. python -m pytest -q
```

## Beta acceptance
1. Begin with two **USD** campaigns in the same draft, total USD 12,000, allocations USD 8,000 and USD 4,000.
2. Ask `decrease the total budget to 9000`. The proposal should update the existing draft, not search new campaigns. Final amounts should be USD 6,000 and USD 3,000.
3. Recreate the previous clarification sequence (`yes adjust ...` then `usd`); those replies should complete the pending intent and never propose unrelated campaigns.
4. Ask `increase the total budget by 1000`, `undo`, `remove the second campaign`, and a new budget amount. Review all draft/undo states.
5. Open another browser/session and check the authenticated conversation and draft are retained according to the existing synchronization rules.
6. Confirm that `make a new plan for education` never silently modifies the existing selection, and a mismatched currency does not convert money.
7. Test payment in test mode separately; this release does **not** initiate payment or change checkout.

## Limitations
- Context is bounded by the Joomla conversation window. It is not unrestricted autonomous memory.
- Structured model interpretation requires working OpenAI credentials and has not been evaluated against the live beta model in this packaged offline test environment.
- Only draft financial edits are executed in this change; saving an account plan and making a donation remain explicitly separate.
