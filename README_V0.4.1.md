# Filantrophy AI v0.4.1 — Contextual Giving-Plan Follow-Ups

## Fixed

- The assistant remembers campaign IDs from the previous recommended results (provided by the Filantrophy server, not from user-entered chat).
- "Add three of them to donate 10000" uses those exact campaigns. If all have one currency (for example USD), it uses that currency only when the user did not specify one.
- If the user specifies a conflicting currency (for example NGN when the campaigns accept USD), the assistant asks instead of converting or dropping campaigns.
- A mixed-currency list, expired results, too many campaigns, or ambiguous subsets return a clarification, never a fabricated successful plan.
- Proposed giving plans do NOT charge a card. The Joomla interface safely fills the draft, which the user reviews before an explicit checkout step.
- New Chat clears server-side remembered recommendation references.

## Upgrade

1. Keep the existing Python `.env` and service secret. Extract the FastAPI ZIP over the existing Python project, then redeploy/restart.
2. Confirm `GET /health` reports `0.4.1`.
3. Install **mod_filantrophy_ai v0.3.1** over the current module, without uninstalling. Keep its existing Python URL and shared secret.
4. Clear the site's cache and refresh.

## Test

1. Send `Show me three healthcare campaigns` in the assistant.
2. Send `Add three of them to donate 10000`.
3. The same three campaign IDs must appear in My Giving Plan; the total should be 10,000 in their common currency and individual amounts must add up exactly.
4. If the campaigns accept USD, but you explicitly say `Donate ₦10,000 to those three`, the assistant must ask about the mismatch without creating a plan.
5. Use New Chat; `Donate 10000 to those three` must ask you to select/show campaigns first.
6. The final payment must still require explicit review and confirmation; do not test with real cards until sandbox reconciliation has passed.

## Safety Notes

The remembered list is scoped to the current Joomla session, current module instance and signed-in user ID, and expires after 30 minutes. Python receives it only in the server-signed request, validates the IDs against the fresh eligible campaign catalogue, and creates no database write or card charge.

Payment status/ledger logic is unchanged in this patch. One-payment Stripe/Paystack checkout remains a separate backend workflow requiring sandbox verification.
