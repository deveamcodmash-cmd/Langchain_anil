# Filantrophy AI v0.5.10 — Contextual Planning / Transaction Sprint

Pairs with **mod_filantrophy_ai v0.5.18**, built from v0.5.9/v0.5.17.

## Added
- Atomic, reversible giving-plan multi-clause proposals. A visitor can remove a selected campaign and set or adjust the overall budget in a single instruction.
- Guarded optional LangChain structured-output planner for unfamiliar multi-clause phrasing; all amounts and ordinal references must appear in the actual current user message. No payment/bookings/account records may be created by this planner.
- Fail-closed multi-action detection. If a compound draft instruction is ambiguous, no unsafe single-action approximation is submitted.
- Model and offline regression tests for positional accuracy, currencies, hypotheticals, comma-formatted numbers, forged amounts and replay-safe frontend acknowledgement.
- Joomla can now sync descriptive **last draft action** receipts alongside existing account conversation and plan snapshots. Receipts are not trusted financial records.

## Important constraints
- This is **not** a durable LangGraph database checkpointer or unrestricted action agent. It builds on Joomla's existing account conversation store. A future phase can add a scoped checkpoint store and broaden transactional support after schema and authorization audits.
- Only the Joomla browser can commit the guarded local draft. Financial checkout, saved giving-plan, coupon, account and booking mutations remain with the original authorized backend.
- Do not overwrite production `.env` or claim booking/payment success based on AI messages.
