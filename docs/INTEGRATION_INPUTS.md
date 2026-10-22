# Filantrophy AI — What We Need For The Next Integration Phase

## Already Available In This Conversation

- FastAPI/LangGraph v0.3.0 source package (used to build v0.4.0).
- Filantrophy AI Assistant module v0.3.0.
- Campaign module v1.0.242 and the older Impact Donor Dashboard v1.4.60 package.
- Existing card checkout and giving-plan workflow descriptions.
- A working cPanel → tunnel → FastAPI deployment architecture (as previously tested).

These are enough for the **foundation release**. Do not share new secrets to get started.

## Required Next — Priority Order

### 1. Current Module Packages

Please upload the **latest versions actually installed on your beta site**, especially when they differ from the copies already shared:

- `mod_cccharity_donor_dashboard` (volunteering, attendance, campaign ownership).
- Event booking module/component or the relevant event registration integration.
- Service Provider listing/booking module/component.
- Corporate, Individual and public profile/directory components where the assistant should access account information.
- Ranking and verified-review modules for analytics in a later phase.

The existing `com_cccharity` component and its tables will remain untouched according to the project boundary. New AI integrations will use the permitted module-owned storage/API layers.

### 2. Data & API Contracts (Sanitized)

For each module, please provide its key read-only query methods/API routes, record status rules, database **schema exports without user data**, public URLs and pagination method. Provide a few **fictional** or anonymized test records per entity (campaign, opportunity, event, service).

### 3. Role And Approval Rules

Approve which actions are available to Guest, Individual, Corporate, Volunteer, Event Organiser, Service Provider and Administrator. Confirm who owns a campaign, event or service and whether the system supports a separate employee/coordinator role. We must not derive write permission from a text prompt.

### 4. Trustworthy Knowledge Content

Provide current approved FAQs, donation/platform fee policies, refunds/cancellations, verification language, volunteer policies, event rules, service booking terms, profile visibility, privacy and support escalation instructions. Content should include its owner and effective date.

### 5. Staging Setup

- A stable **non-production** FastAPI endpoint for end-to-end testing. The shared secret remains privately in the Joomla module and Python environment.
- Ability to install the updated AI module on the beta website.
- Test accounts for each role created locally by the team (do not share passwords in chat).
- Payment-provider sandbox configuration on the existing backend (do not send credentials in chat).

## First Decision Needed

**Which domain should be integrated after campaign/giving-plan actions: Volunteering & Events, or Service Providers?** The foundation supports both; implementing one end to end first will give us a reusable secure tool pattern.

## What Is *Not* Needed

No raw production database dump, OpenAI key, payment secret, private user conversations, real donor records, access passwords, or live card details. Use sanitized exports and local staging configuration.
