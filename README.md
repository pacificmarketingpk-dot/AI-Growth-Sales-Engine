# AI Growth Sales Engine

An AI-assisted B2B prospecting and sales workspace for a digital marketing consultant. AI does the research, scoring, drafting and conversation analysis; you build the relationship, run the consultation and close.

```
Prospect → Research → AI analysis → Lead score → Personalised outreach → Reply
        → Intent detection → Qualification → Human takeover → Meeting → Client
```

Nothing is sent on your behalf. There is no LinkedIn scraping, no browser automation and no password collection: messages are drafted for you to copy and send, and every integration is either real (OAuth / official API) or clearly shown as not connected.

---

## Contents

1. [What's included](#whats-included)
2. [Project structure](#project-structure)
3. [Quick start with Docker](#quick-start-with-docker)
4. [Local development](#local-development)
5. [Environment variables](#environment-variables)
6. [Connecting AI](#connecting-ai)
7. [Connecting Google Calendar and Sheets](#connecting-google-calendar-and-sheets)
8. [Deploying to a VPS](#deploying-to-a-vps)
9. [Testing](#testing)
10. [Security](#security)
11. [What's optional or not included](#whats-optional-or-not-included)
12. [Troubleshooting](#troubleshooting)

---

## What's included

| Area | What it does |
|---|---|
| Dashboard | Prospect, pipeline, AI and meeting metrics, all computed from your database. Demo data can be toggled in or out. |
| Prospects | Add, edit, search, filter, sort, bulk-select. Table on desktop, cards on mobile. CSV and Google Sheets import, CSV export. |
| Prospect discovery | Criteria form (country, industry, size, titles, keywords, minimum score). Searches only connected, permitted data providers; with none connected it says so and offers CSV / Sheets import. |
| AI analysis | Lead score 0–100 with the six-part breakdown (fit 20, marketing 25, potential 15, decision maker 15, digital 15, outreach 10), business problem, growth opportunity, one primary service (optional secondary), personalisation, and evidence labelled Fact / Assumption / Opportunity. Optional homepage review, only when the page was actually fetched. |
| Bulk analysis | Bounded queue with progress ("Analyzing 3 / 10"), retries, and per-prospect failure isolation. |
| Cost control | No silent re-analysis; every run stores version, model, tokens and estimated cost. Usage totals on the AI Analysis page. |
| Outreach | Connection message, follow-up 1 and 2, each with Copy, Edit and Regenerate. Tracks channel, date sent and follow-up due dates. |
| Conversations | Paste a thread; AI classifies intent (Interested, High intent, Qualified, Neutral, Not interested, Not relevant, Needs follow-up) and extracts pain point, need, budget/timeline signals, decision maker, current solution, next action and a suggested reply. |
| Qualification | Need, budget, authority, timeline, current solution, urgency → score 0–100 → Hot / Qualified / Nurture / Unqualified. Filled by AI, adjustable by you. |
| Hot Leads & takeover | Ranked lead cards; a "Human takeover required" banner with summary, pain point, suggested response and qualification questions. |
| Meetings & calendar | Book consultations (default "Digital Growth Consultation", 30 min) into Google Calendar via OAuth, or save locally. Each meeting shows the prep brief and holds notes and next action. Calendar page shows your next two weeks and open slots. |
| Analytics | Contact, response, qualification, meeting, proposal and win rates; funnel, weekly trend, score distribution, intent mix. |
| Settings | Profile and app name, AI provider/model, Google connections, prospect sources, tone and follow-up timing, meeting defaults, notifications, password, sessions, API token, demo data, audit log. |
| Demo mode | Five fake prospects named `DEMO …`, tagged everywhere, excluded from analytics by default, removable in one click. AI on demo records uses canned output and costs nothing. |

---

## Project structure

```
.
├── docker-compose.yml        # PostgreSQL + API + Nginx (+ optional Caddy for HTTPS)
├── .env.example              # every setting, documented
├── deploy/Caddyfile          # automatic HTTPS (optional)
├── docs/ARCHITECTURE.md      # design notes, extension points, scaling
├── e2e/                      # browser acceptance + responsive checks (Playwright)
├── backend/
│   ├── Dockerfile, docker-entrypoint.sh   # runs migrations, then the API
│   ├── alembic/              # database migrations
│   ├── app/
│   │   ├── main.py           # app factory, security middleware, error handling
│   │   ├── config.py         # settings from environment variables
│   │   ├── api/              # REST routes (prospects, conversations, leads, meetings, …)
│   │   ├── auth/             # password hashing, JWT sessions, ownership checks
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # request/response validation
│   │   ├── services/
│   │   │   ├── ai/           # provider.py, openai_provider.py, anthropic_provider.py,
│   │   │   │                 # prompts.py, schemas.py (strict AI output validation)
│   │   │   ├── google/       # OAuth, Calendar, Sheets
│   │   │   └── …             # analysis, conversations, scoring, CSV, website, audit
│   │   ├── providers/        # interfaces for future integrations (LinkedIn API, CRM, data providers)
│   │   └── utils/            # token encryption, rate limiting
│   └── tests/                # 63 pytest tests incl. the full acceptance workflow
└── frontend/
    ├── Dockerfile, deploy/   # build + Nginx config (SPA, /api proxy, security headers)
    └── src/
        ├── pages/            # one file per screen
        ├── components/       # UI kit, score bar, modals, schedulers
        ├── layouts/          # sidebar / mobile drawer shell
        ├── hooks/ services/ types/ utils/
```

---

## Quick start with Docker

Requirements: Docker with Compose v2.

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY and POSTGRES_PASSWORD at minimum, plus one AI key.
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # use for SECRET_KEY

# For a first local try, point the URLs at localhost:
#   FRONTEND_URL=http://localhost  BACKEND_URL=http://localhost  CORS_ORIGINS=http://localhost

docker compose up -d --build
```

Open http://localhost. The first account you create owns the workspace. Afterwards set `ALLOW_REGISTRATION=false` in `.env` and run `docker compose up -d` so nobody else can sign up.

On a plain `http://localhost` the session cookie is marked `Secure` in production mode. Most browsers accept that on localhost; if sign-in doesn't stick, use HTTPS (see [Deploying to a VPS](#deploying-to-a-vps)) or run the development setup below.

---

## Local development

Requirements: Python 3.12, Node 20+, PostgreSQL 14+ (or SQLite for a quick look).

**Backend**

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# PostgreSQL (recommended):
createdb age
export DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/age
# …or SQLite for a throwaway try:  export DATABASE_URL=sqlite:///./dev.db

export SECRET_KEY=dev-only-change-me
export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY + AI_PROVIDER=openai
alembic upgrade head                   # optional in dev: tables are auto-created
uvicorn app.main:app --reload --port 8000
```

API docs (development only): http://localhost:8000/api/docs

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

**Database changes**: edit `backend/app/models/entities.py`, then

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

---

## Environment variables

All configuration is server-side. Nothing in `.env` is ever sent to the browser. See `.env.example` for the full annotated list.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Signs sessions and encrypts stored OAuth tokens. 32+ random characters; the API refuses to start in production without it. Changing it signs everyone out and invalidates stored Google tokens (reconnect afterwards). |
| `POSTGRES_PASSWORD` | Docker | Database password; Compose builds `DATABASE_URL` from it. |
| `DATABASE_URL` | Non-Docker | e.g. `postgresql+psycopg://user:pass@host:5432/age` |
| `FRONTEND_URL`, `BACKEND_URL` | Yes | Public URLs. Same value with the default Docker setup. Used for OAuth redirects. |
| `CORS_ORIGINS` | Yes | Comma-separated allowed browser origins. |
| `ALLOW_REGISTRATION` | No | `false` after creating your account. |
| `AI_PROVIDER` | No | `anthropic` (default) or `openai`. |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | One AI key | Claude access. |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | One AI key | OpenAI access. |
| `AI_MAX_CONCURRENCY`, `AI_MAX_RETRIES` | No | Bulk analysis parallelism (default 2) and retries for invalid AI output (default 2). |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | For Google | OAuth client for Calendar and Sheets. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | For alerts | Qualified-lead emails to you only. |
| `DOMAIN` | For HTTPS | Your domain when using the `tls` profile. |
| `WEB_BIND`, `WEB_PORT` | No | Where Nginx listens on the host. |

---

## Connecting AI

1. Get a key from https://console.anthropic.com or https://platform.openai.com.
2. Put it in `.env` (`ANTHROPIC_API_KEY=` or `OPENAI_API_KEY=`), and set `AI_PROVIDER` to match.
3. `docker compose up -d` to apply.
4. In the app, **Settings → AI** shows which providers have a key. You can pick a provider and model per account; leave the model blank for the server default.

How the AI is kept honest:

- Prompts require every claim to be labelled Fact, Assumption or Opportunity, forbid inventing revenue, traffic, headcount, ad spend, clients or budgets, and require "Insufficient evidence." for unknowns.
- Every response is validated against a strict schema (`backend/app/services/ai/schemas.py`): score components within their maximums, services from the fixed category list, no generic openers like "I came across your profile" or "We are a leading digital marketing agency". Invalid output is retried with the validator's error, and never saved if it still fails.
- The lead score is always recomputed on the server from the breakdown.
- Website findings only appear when the homepage was actually retrieved; otherwise the app shows "Website analysis unavailable."

Estimated costs use list prices in `backend/app/services/ai/provider.py` (`PRICING`). Update them if prices change.

---

## Connecting Google Calendar and Sheets

You sign in on Google's own page; the app never sees your Google password. Tokens are stored encrypted with `SECRET_KEY`.

1. Go to https://console.cloud.google.com and create (or pick) a project.
2. **APIs & Services → Library**: enable **Google Calendar API**, **Google Sheets API** and **Google Drive API** (Drive is used only to list your spreadsheets, read-only metadata).
3. **APIs & Services → OAuth consent screen**: choose *External*, fill in the app name and your email, and add these scopes:
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive.metadata.readonly`

   While the app is in *Testing* status, add your own Google account under **Test users**. Test-mode refresh tokens expire after 7 days; the app will show "Expired, reconnect" and you click Reconnect. Publishing the consent screen removes that limit (Google may ask for verification because of the Calendar/Sheets scopes).
4. **Credentials → Create credentials → OAuth client ID → Web application.** Under **Authorised redirect URIs** add exactly:
   ```
   https://your-domain.com/api/integrations/google/callback
   ```
   (For local Docker: `http://localhost/api/integrations/google/callback`. It must match `BACKEND_URL` + `/api/integrations/google/callback`.)
5. Copy the client ID and secret into `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, then `docker compose up -d`.
6. In the app: **Settings → Google → Connect Google Calendar**, then **Connect Google Sheets**.

Using them:

- **Calendar**: "Book consultation" creates the event on your primary calendar. Optionally add the prospect as a guest; Google is told not to email them (`sendUpdates=none`), so you decide when to send the invite. The Calendar page shows your next 14 days and open weekday slots.
- **Sheets**: Prospects → *Google Sheet*: choose a spreadsheet and tab (first row = headers, a *Name* column is required), preview, import. Settings → Google → *Export results* writes prospects with scores and recommendations to a tab, starting at A1 (it overwrites that tab's contents).

---

## Deploying to a VPS

Tested topology: Nginx serves the built frontend and proxies `/api` to the API on the same origin, so session cookies are first-party and no CORS is needed. The API container applies database migrations on every start.

**1. Server.** Any Linux VPS with 1 GB+ RAM (Ubuntu 24.04 works well). Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

**2. DNS.** Point an A record (e.g. `sales.example.com`) at the server's IP.

**3. Code and configuration.**

```bash
git clone <your-repo> ai-growth-sales-engine && cd ai-growth-sales-engine   # or upload the zip
cp .env.example .env
nano .env
```

Set at least: `SECRET_KEY`, `POSTGRES_PASSWORD`, one AI key, and

```
FRONTEND_URL=https://sales.example.com
BACKEND_URL=https://sales.example.com
CORS_ORIGINS=https://sales.example.com
DOMAIN=sales.example.com
WEB_BIND=127.0.0.1
WEB_PORT=8080
```

**4. Start with automatic HTTPS** (Caddy fetches and renews a Let's Encrypt certificate):

```bash
docker compose --profile tls up -d --build
docker compose logs -f backend     # watch for "Applying database migrations..." then startup
```

Open https://sales.example.com, create your account, then set `ALLOW_REGISTRATION=false` and run `docker compose --profile tls up -d`.

If you already run your own reverse proxy (Nginx, Traefik, a load balancer), skip the `tls` profile: run `docker compose up -d --build`, and point your proxy at `WEB_BIND:WEB_PORT`. Make sure it terminates HTTPS. Note: the bundled Nginx sets `X-Real-IP` from the connection it receives, so with an extra proxy in front, rate limits will see that proxy's IP unless you configure Nginx's `real_ip` module for it.

**5. Firewall.** Allow only 22, 80 and 443:

```bash
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

**Updating**

```bash
git pull && docker compose --profile tls up -d --build    # migrations run automatically
```

**Backups**

```bash
# backup
docker compose exec -T db pg_dump -U age age | gzip > backup-$(date +%F).sql.gz
# restore into an empty database
gunzip -c backup-2026-10-04.sql.gz | docker compose exec -T db psql -U age age
```

Schedule the backup with cron and copy the files off the server. Also keep a copy of `.env`: without the same `SECRET_KEY`, stored Google tokens can't be decrypted (you'd just reconnect).

---

## Testing

**Backend** (63 tests: auth, CRUD, authorisation between users, AI JSON validation, lead scoring, CSV import and duplicates, conversation classification, qualification, meetings and calendar, dashboard maths, demo isolation, audit log, SSRF and IP-spoofing protections, and the full 24-step acceptance workflow). No AI key or Google account needed; AI calls use a fake provider.

```bash
cd backend
pytest                                   # SQLite
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/age_test pytest   # PostgreSQL
```

**Frontend**

```bash
cd frontend && npm run typecheck && npm run build
```

**Browser end-to-end** against a running, empty instance (works without AI keys or Google):

```bash
pip install playwright && playwright install chromium
BASE_URL=http://localhost python e2e/acceptance.py    # the acceptance workflow, 15 steps
BASE_URL=http://localhost python e2e/responsive.py    # every page at 390–1440px
```

What has been verified: all 63 backend tests on both SQLite and PostgreSQL 16; migrations upgrade, downgrade and re-upgrade cleanly and match the models; the 15-step browser acceptance run and the responsive check on the production setup (Nginx config from this repo, production mode, PostgreSQL, migrations applied) with no Content-Security-Policy violations. The Dockerfiles and Compose file themselves were not built in that environment (Docker wasn't available); they wrap exactly the commands that were tested.

---

## Security

- Passwords hashed with bcrypt; sessions are signed JWTs in an `httpOnly`, `SameSite=Lax` cookie (`Secure` in production). Changing your password or "Sign out other sessions" revokes all existing sessions and API tokens.
- Every record is scoped to its owner; requests for another user's data return 404.
- CSRF protection: state-changing requests must carry a custom header that browsers can't send cross-site.
- Input validated on every endpoint; SQL via SQLAlchemy parameters only; React escapes output; strict Content-Security-Policy and security headers from Nginx and the API.
- Rate limits on sign-in, registration and AI endpoints, keyed on the real client IP (spoofed `X-Forwarded-For` is ignored).
- Website fetching blocks private, loopback and link-local addresses (SSRF protection) and caps page size.
- CSV export neutralises spreadsheet formula injection.
- OAuth tokens encrypted at rest; OAuth `state` checked and single-use.
- Users never see stack traces; errors are logged server-side.
- API docs are disabled in production.

---

## What's optional or not included

**Optional, works once configured**: Google Calendar, Google Sheets, qualified-lead email notifications (SMTP), automatic HTTPS (Caddy).

**Deliberately not included in V1**

- **Sending LinkedIn messages or connection requests.** LinkedIn's messaging APIs are restricted to approved partners. The app drafts messages for you to copy and send; Settings shows LinkedIn as *Not connected*. `backend/app/providers/base.py` has the `MessagingChannel` interface for an official integration later.
- **Automated discovery from a data provider.** Discovery searches only licensed providers you connect. None is bundled because they need a paid contract and API key. Implement `ProspectingSource` in `providers/base.py` and register it; the Discovery form and Settings pick it up automatically.
- **Automated emails to prospects.** Not sent in V1, by design.
- **CRM sync.** `CRMConnector` interface is ready; use CSV export meanwhile.
- **Multi-user teams and roles.** The data model is per-user; V1 is optimised for one professional. See `docs/ARCHITECTURE.md` for the path to teams.
- **Horizontal scaling.** Runs as one API process because OAuth state, the bulk-analysis queue and rate limits are in memory. Plenty for a single consultant; move them to Redis before adding workers or servers.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "AI analysis is temporarily unavailable … No API key is configured" | Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to `.env` and match `AI_PROVIDER`; `docker compose up -d`. |
| "AI analysis is temporarily unavailable" (with a key) | Check the key, model name and account credit; `docker compose logs backend` shows the provider's HTTP status. |
| Google button disabled, "Google OAuth isn't set up on the server" | Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, restart. |
| Google error `redirect_uri_mismatch` | The redirect URI in Google Cloud must equal `BACKEND_URL` + `/api/integrations/google/callback`, including https and no trailing slash. |
| Google says "access blocked" | Add your account under Test users on the OAuth consent screen. |
| Calendar shows "Expired, reconnect" after a week | Consent screen is in Testing mode; reconnect, or publish the app. |
| Signed out right after signing in | Production cookies need HTTPS. Use the `tls` profile, or develop with `npm run dev`. |
| API container exits with "SECRET_KEY must be set…" | Set a random `SECRET_KEY` of 32+ characters. |
| "Too many requests" | Rate limit hit; wait a minute. |
