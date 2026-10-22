# Filantrophy AI Platform — Capability & Implementation Blueprint v0.4.0

**Date:** 20 October 2026  
**Purpose:** Define the platform-wide AI architecture and the client-approved experience before enabling additional record-changing tools.  
**Status:** Phase 1 foundation implementation with platform action integrations pending.

## 1. Product Direction

Build a single Filantrophy Intelligence Engine for chat, search, smart forms, dashboards, recommendations, support, volunteering, events, service providers, corporate impact, and administration. Visitors see **Filantrophy**, not implementation/provider names. The site retains its existing design language: deep green, Inter, Title Case UI labels, accessible minimum 14px type, and clear feedback for every action.

**Principle:** AI interprets intent and proposes actions; trusted platform APIs authenticate, validate, execute, and confirm the actual outcome. Never present a draft as a completed donation, registration, booking, moderation action, or payment.

## 2. Baseline Source Inspected

- Python FastAPI/LangGraph v0.3.0 (uploaded in this project).
- Filantrophy AI Joomla Module v0.3.0 (uploaded in this project).
- The existing campaign and dashboard packages are available in the working session but **not modified** by this foundation release.
- The v0.3.0 backend contained a campaign-only catalogue, a 30-campaign context boundary, a local draft-action parser, and a knowledge prompt with stale payment wording.

## 3. Current Foundation Delivery

| Area | Included in v0.4.0 | Production limitations |
|---|---|---|
| Platform Capability Registry | 20 named capabilities across 9 domains with status, role, approval and execution type | Proposed role eligibility must be approved against real Filantrophy ACL |
| Read-Only Capability API | Signed `POST /v1/capabilities` | Joomla UI does not consume it yet |
| Conservative Policy Preflight | Signed `POST /v1/policy-check` | Informational only; never authorizes business transactions |
| Trusted Knowledge Starter | Reviewed statements on branding, campaign catalogue, plans, payments, privacy, and planned tools | Not yet document-indexed RAG; requires real approved policies |
| Future Action Guard | Prevents AI from claiming it booked services, registered events, applied to volunteer roles, or published campaigns without integration | Must extend as additional tools are added |
| Sensitive Data Guard | Blocks likely card numbers or access credentials before the model is called | Defense in depth, not a full data-loss prevention system |
| Typed Tool Contracts | Search and plan-edit models for campaigns, events, volunteers and services; version and idempotency keys | Schemas only; no new platform mutation endpoints |
| Evaluation Harness | 30 offline prompt scenarios plus automated Python API/role tests | Does not evaluate actual model accuracy or payment flows |
| Interactive UX Prototype | Role filter, capability explorer, user journeys | Illustrative only, no live platform actions |

## 4. Target Architecture

```text
Filantrophy User Experience
  Chat / Search / Forms / Dashboards / Admin Tools
            |
     Secure Filantrophy Action Gateway
     Identity / ACL / CSRF / Audit / Validation
            |
      Signed HTTPS Request
            |
         FastAPI
            |
  Intent & Safety Guard → LangGraph Supervisor
            |
  Campaigns | Giving | Volunteering | Events
  Services  | Corporate | Impact | Support
            |
  Typed Tool Registry + Capability Policy
            |
   Existing Authoritative Filantrophy APIs
            |
  Campaign / Event / Booking / Account Data

Payment execution, financial records and receipts always remain
with the trusted Filantrophy payment and ledger services.
```

The tunnel or Render endpoint is a transport layer, not an authorization mechanism. Every server request must be signed. The assistant must never accept role or user ownership claims as proof from user text. Only Filantrophy server-side authentication may supply user role and identity in signed requests.

## 5. Role-Aware UX & Access Model — Proposed, Not Yet Finalized

| Role | Useful AI Features | Higher-Risk Actions |
|---|---|---|
| Guest | Public campaign/event/service discovery, support | No private history or saved-user updates |
| Individual | Giving plans, donations, receipts, profiles, event/volunteer discovery | Explicit confirmation for payments and submissions |
| Corporate | CSR budgets, approved impact metrics, participation planning | Organisation ownership and finance permissions |
| Volunteer | Applications, personal attendance and hours | Identity verification and consent before applications |
| Event Organiser | Event drafting, coordinator workflows, verified attendance | Organiser ACL and approvals for publish/attendance updates |
| Service Provider | Listings, services, staff and booking insights | Provider ownership and approval for changes |
| Administrator | Operational triage, moderation recommendations, audit reports | Separate privileged approval, audit trail, never unrestricted SQL |

**Security requirement:** The catalogue eligibility matrix is a design aid. Real permissions must be enforced by the appropriate backend API and existing user/group/record ownership checks.

## 6. User Journeys (First Approval Scope)

**Donation planning:** "Give ₦20,000 to healthcare" → identify cause and currency → retrieve eligible campaigns → propose plan → confirm allocations → disclose fee → customer approves embedded checkout → trusted gateway verifies → record campaign donations → show verified summary.

**Budget change:** "Make it ₦10,000" → identify active draft → check plan version → recalculate deterministic amounts → update authoritative draft → return structured event and new version → update every visible UI field. Never claim it changed if the service rejected it.

**Volunteer search:** Search/filter verified opportunities. Until the volunteer API is connected, respond with a useful platform navigation option instead of inventing results.

**Service booking:** Ask about date/time only when necessary. Verify actual availability, ownership, and terms. Require confirmation before booking. Until integrated, direct the user to existing booking UI.

**Admin request:** "Approve all" must not execute broadly. Verify privileged role, show exact affected records, require approval, record audit log, and reject actions outside assigned permissions.

## 7. Tool Contract Rules

1. Each tool has a narrow business purpose, typed inputs and outputs, and documented failure codes.
2. Read tools return authoritative live records or explicitly mark stale cached results.
3. Write tools require signed user/role context and record ownership checks.
4. All money amounts are minor units (integers); clients format without unnecessary decimals.
5. Mutations include an **idempotency key** and **expected record version**.
6. Payment, refund, publishing, cancellation, and privileged changes require explicit confirmation.
7. Every result is **success**, **rejected**, **conflict**, **pending**, or **unavailable**. UI uses the backend result; LLM prose is not evidence.
8. Each invocation has an audit reference, rate limits, timeout bounds, and a safe fallback.

**Prototype contracts** are in `app/tool_contracts.py`. They are not executable yet.

## 8. Knowledge & Training Strategy

### Stage A — Grounded Platform Knowledge (Now)
Approved documents: brand style, campaign rules, donation/fee/receipt policy, payment states, onboarding, roles, volunteering, events, service-provider workflows, customer support, and privacy. Curate documents with version, owner, effective date, public/admin classification, and expiry/review date.

### Stage B — Retrieval (Next)
Index only approved documents. Filter retrieval by actor scope. Keep private operational and personal records outside the public knowledge index. Live campaign data comes from APIs rather than embedded documents.

### Stage C — Action Evaluations (Next)
Create a labelled intent/action set for each platform domain and negative examples: unclear requests, incorrect role, stale state, repeated commands, missing records, unusual currencies, and instructions embedded in campaign descriptions.

### Stage D — Fine-Tuning (Later, Only If Measured Benefit)
Fine-tune classification or structured outputs only after a sufficiently large, reviewed and appropriately consented dataset shows that retrieval and tool calling are not meeting evaluation targets. No unreviewed conversation logging into training sets.

## 9. Performance Targets (Proposed)

- Deterministic intent/permission validation: server-side, no model call.
- Read-only searches: paginated and scoped; never return huge unbounded collections.
- Agent tasks: prefer minimal agent routing and fail fast on missing integrations.
- UI: immediate updates from trusted events, loading/empty/error states, keyboard-accessible mobile flows.
- User-facing failures: concise explanations, actionable retry options, no technical implementation details.
- Payment availability: continue supporting existing manual checkout if AI service is offline.

These are design targets, not measured production service-level commitments.

## 10. Worst-Case & Safety Acceptance Tests

- Off-topic prompts are redirected to Filantrophy use cases.
- Code/prompt-injection attempts cannot alter tool permissions or reveal secrets.
- Cross-user/private account access is denied by authoritative ACL.
- Ambiguous "it"/"first" references are resolved against verified current context or clarified.
- Duplicate write requests do not duplicate payments, bookings or applications.
- Stale plan edits produce a **conflict**, not silent overwrites.
- Campaign becomes inactive between recommendation and payment: checkout revalidates.
- Currency mismatch or amount error: checkout blocked with correction.
- Payment succeeds but response times out: status reconciles without second charge.
- Service unavailable: no false success; manual platform route remains available.
- Planned capability requested: explicit unavailable response, not invented confirmation.

## 11. Delivery Sequence

| Phase | Development | Acceptance |
|---|---|---|
| 1 — Foundation | Capability registry, policy preflight, knowledge seed, tests, UX preview | All offline and signed-endpoint tests pass |
| 2 — Read-Only Tools | Campaign pagination, Volunteer/Event/Service search APIs | Accurate filtered records and role access, documented source IDs |
| 3 — Approved Actions | Plan updates, booking/application drafts, event draft tools, versioning/idempotency | Structured state synchronization, no unauthorized writes |
| 4 — Dashboards & Analytics | Personal, Corporate, Impact and Ranking intelligence | Verified data provenance, correct scoping, explainable calculations |
| 5 — Proactive AI | User-opted alerts, milestones, supported multilingual/voice UX | Consent, throttling, privacy, auditability |

## 12. Required Inputs From The Filantrophy Team

See the separate **Filantrophy-AI-What-We-Need.md** checklist for precise file and policy requests. No API keys, payment secrets, or raw personal records need to be sent in chat.

## 13. Honest Status

This blueprint and FastAPI update are a **foundation milestone**. They do not yet make event bookings, volunteer applications, profile mutations, administrative changes or platform-wide retrieval live. The existing AI module remains at v0.3.0 in this delivery, because new write tools must not be added before their authoritative API and permission contracts are reviewed.
