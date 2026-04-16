# ⛳ Golf Reservation Chatbot

[日本語 README](README.md)

A conversational golf booking assistant built to demonstrate practical use of **MCP (Model Context Protocol)** in a real product flow.

The project intentionally separates:

- an **LLM host** that manages conversation state and tool orchestration
- a dedicated **MCP server** for golf-domain tools like tee-time search, booking, and weather-aware recommendations
- **Supabase** for Auth, Postgres, RLS, and transactional reservation RPCs

## What This Project Demonstrates

- the LLM is not treated as the source of truth for reservation data
- domain operations are routed through deterministic **MCP tools**
- the host discovers tool schemas directly from the MCP server instead of duplicating them
- conversation memory is handled explicitly instead of relying only on raw chat history
- the production runtime path is fully aligned around Supabase rather than split across two data stores

## Tech Stack

- **Backend:** FastAPI, Python, MCP, OpenAI
- **Frontend:** React, TypeScript, Vite
- **Data:** Supabase Postgres
- **Auth:** Supabase Auth
- **Conversation state:** memory by default, optional Redis backend
- **Local test fallback:** SQLite fixtures

## Architecture

```text
User -> FastAPI Host -> OpenAI LLM -> MCP Client -> MCP Server -> Supabase Postgres
                         |                              |
                         +-> conversation state -> Memory or Redis
                         +-> Supabase JWT verification / profile sync
```

- **Host (FastAPI)**
  - conversation state
  - confirmation logic
  - follow-up resolution
  - MCP tool discovery and orchestration
  - Supabase JWT verification
- **MCP Server (FastMCP)**
  - tee-time search
  - course lookup
  - alternatives and recommendations
  - reservation create / confirm / cancel
  - weather checks
- **Supabase**
  - Auth
  - Postgres tables / views / RLS
  - transactional RPC for reservation writes

## Supabase In This Project

- frontend authentication uses Supabase Auth
- backend profile routes verify Supabase JWTs and sync user profiles
- public read flows use Postgres views with `security_invoker`
- reservation writes run through Postgres RPC functions so slot updates and history writes stay transactional
- RLS policies use the `select auth.uid()` pattern recommended by Supabase for better performance

SQLite remains only as a local test harness, not as a second runtime source of truth.

## Features

- tee-time search
- weather-aware recommendations
- default filtering for rain and wind above 20 km/h
- home area / travel mode / max travel time preferences
- reservation creation, hold, confirmation, and cancellation
- structured conversational memory
- JPY price presentation for a Japan-based booking domain

## Local Development

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd frontend
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Set at minimum:

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

Before sharing the repo, also set:

- `CORS_ALLOW_ORIGINS`

If you want Redis-backed conversation state, also set:

- `CONVERSATION_BACKEND=redis`
- `REDIS_URL=redis://localhost:6379/0`

If you want MCP tool discovery to refresh every request during development, set:

- `MCP_DISABLE_TOOL_CACHE=1`

### 3. Apply Supabase migrations

```bash
supabase db push
```

### 4. Run

Backend:

```bash
./scripts/start_server.sh --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

## Docker

Docker support is included for backend, frontend, and Redis.

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Start everything with:

```bash
docker compose up --build
```

Exposed endpoints:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Redis: `redis://localhost:6379`

## Supabase Migrations

- `supabase/migrations/20260416183000_init_golf_reservation.sql`
- `supabase/migrations/20260416190000_runtime_views_and_rls.sql`
- `supabase/migrations/20260416210000_complete_supabase_cutover.sql`

The final migration fixes the original mixed state by:

- converting exposed views to `security_invoker`
- adding a `reservation_details` view
- updating RLS policies to match Supabase performance guidance
- adding transactional reservation RPC functions
- seeding sample courses and tee times

## Engineering Tradeoffs

- public reads use Supabase views plus RLS
- write-heavy reservation flows use RPC because they need multi-table transactions
- conversation state stays in the backend because prompt-only memory is not reliable enough for booking flows
- SQLite is retained only for tests and offline fixtures
- `/chat` requires authentication so the backend does not expose unauthenticated OpenAI spend
- the MCP server now stays connected for the lifetime of the FastAPI process and tool calls are serialized with a lock; if throughput becomes a concern, the next step is a small connection pool

## Project Structure

```text
golf-reservation/
├── backend/
│   ├── host/                # FastAPI host
│   ├── mcp_server/          # MCP server
│   ├── services/            # weather / location / supabase helpers
│   └── db/
├── frontend/
├── supabase/
├── scripts/
├── tests/
└── docker-compose.yml
```

## License

MIT
