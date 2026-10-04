# Architecture notes

## Request flow

```
Browser ──HTTPS──> (Caddy, optional) ──> Nginx ──/api──> FastAPI ──> PostgreSQL
                                           └── static SPA (React build)
FastAPI ──> Anthropic / OpenAI APIs        (AI analysis)
FastAPI ──> Google OAuth, Calendar, Sheets (user-authorised)
FastAPI ──> prospect websites              (optional homepage review, SSRF-guarded)
```

Frontend and API share one origin in production, so the session is a first-party `httpOnly` cookie and the browser never holds an API key or token it could leak.

## Backend layers

- `api/` — HTTP only: parse, authorise (every query is scoped to `user_id`), call a service, shape the response.
- `services/` — business logic, no HTTP. `analysis_service`, `conversation_service`, `csv_import`, `scoring` (pure functions), `website`, `audit`, `notifications`, `google/*`.
- `services/ai/` — the provider boundary. Business logic calls `AIProvider.generate(system, user, Schema)` and gets a validated Pydantic object or an `AIError`. Switching provider never touches business code.
- `providers/base.py` — interfaces for integrations that don't exist yet (`ProspectingSource`, `MessagingChannel`, `CRMConnector`). They are listed in Settings as *Not connected*; nothing pretends to work.

## AI pipeline (one prospect)

1. Refuse if already analysed unless `force=true` (cost control).
2. If a website exists: fetch homepage (public IPs only, 1.5 MB cap, 3 redirects), extract title/meta/headings/CTAs/forms, ask the model for structured findings.
3. Main analysis prompt with prospect data, consultant profile, and website facts *only if retrieved*.
4. Validate (`ProspectAnalysisResult`): bounded score components, allowed service categories, banned generic phrases, server-side score total. On failure the validator error is fed back and retried (`AI_MAX_RETRIES`).
5. Save a new `ProspectAnalysis` version with model, tokens and estimated cost; refresh un-edited outreach drafts (your edits are never overwritten).

Bulk analysis runs the same function per prospect inside an asyncio task, limited by a semaphore (`AI_MAX_CONCURRENCY`); each failure is recorded on the job and the loop continues.

## Conversation → qualification

`ConversationAnalysisResult` returns intent plus six qualification signals with fixed maximums (need 25, budget 15, authority 20, timeline 15, current solution 10, urgency 15). The server sums them (clamped) into the qualification score. The prospect becomes `QUALIFIED` when intent is High intent / Qualified **and** the score is ≥ 60, and is flagged for human takeover when the model recommends it or intent is high. Proposal / Won / Lost prospects are never moved backwards.

## Funnel definitions (dashboard and analytics)

Stages are cumulative by status, so a prospect at `PROPOSAL` also counts as contacted, responded and qualified.

- Contacted: status Contacted or later, or a recorded contact date
- Responses: Replied / Qualified / Proposal / Won, plus Lost prospects that have a conversation
- Response rate = responses ÷ contacted · Qualification rate = qualified ÷ responses
- Meeting rate = prospects with a meeting ÷ qualified · Proposal rate = proposals ÷ prospects with a meeting
- Win rate = won ÷ proposals

Demo records are excluded from analytics unless you tick *Include demo data*.

## Adding an integration

**A prospect data provider**: subclass `ProspectingSource`, implement `configured()` (e.g. API key present) and `search(criteria)` returning dicts with prospect fields, then append an instance to `PROSPECTING_SOURCES`. Discovery and Settings use it automatically. Only use providers whose terms permit this use.

**Official LinkedIn messaging** (requires LinkedIn partner approval): implement `MessagingChannel.send`, add an OAuth flow like `services/google/oauth.py`, and show a *Send* button only when `configured()` is true. Until then the UI shows *Copy* and "LinkedIn integration not connected."

## Scaling beyond one process

Three things live in process memory: the OAuth `state` map, the bulk-analysis task runner, and the rate limiter. For multiple workers or servers, move OAuth state and rate limits to Redis, and the bulk queue to a worker (RQ, Celery, Arq). The job table (`analysis_jobs`) already persists progress, so the UI wouldn't change.

## Path to teams

Every owned row has `user_id`. For agencies, add an `organizations` table, an `organization_id` on owned rows, and a membership/role table; replace the `user_id` filters in `auth/deps.py` and the routes with an organisation scope.
