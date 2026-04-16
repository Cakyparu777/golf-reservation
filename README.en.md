# ⛳ Golf Reservation Chatbot

[日本語 README](README.md)

A conversational golf booking assistant built to demonstrate practical use of **MCP (Model Context Protocol)** in a real product flow.

The project combines:

- an **LLM host** that manages conversation state and tool orchestration
- a dedicated **MCP server** for golf-domain tools like tee-time search, booking, and weather-aware recommendations
- an incremental **Supabase migration** showing MCP + Auth + Postgres integration in a production-oriented direction

This repository is intentionally portfolio-oriented. The goal is not only to make the chatbot work, but to show architecture decisions around tool use, structured memory, and backend integration.

## What This Project Demonstrates

- the LLM is not treated as the source of truth for reservation data
- domain operations are routed through deterministic **MCP tools**
- conversation memory is handled explicitly instead of relying only on raw chat history
- the system can evolve from local development architecture into a more production-ready stack with **Supabase Auth + Postgres**

In short, this project is meant to show that I can use MCP comfortably in a full-stack application, not just in isolated demos.

## Tech Stack

- **Backend:** FastAPI, Python, MCP, OpenAI
- **Frontend:** React, TypeScript, Vite
- **Data:** SQLite today, Supabase Postgres migration in progress
- **Auth:** local JWT flow + Supabase Auth support
- **Infra direction:** Supabase, RLS, MCP-connected tooling

## Architecture

```text
User -> FastAPI Host -> OpenAI LLM -> MCP Client -> MCP Server -> SQLite / Supabase-ready Postgres
```

- **Host (FastAPI)**
  - conversation state
  - confirmation logic
  - follow-up resolution
  - tool orchestration
- **MCP Server (FastMCP)**
  - tee-time search
  - course lookup
  - alternatives and recommendations
  - reservation create / confirm / cancel
  - weather checks
- **LLM (OpenAI)**
  - intent interpretation
  - response generation
  - tool selection

## MCP In This Project

The assistant does not “guess” booking data.

- golf-domain operations are split into **MCP tools**
- the host layer handles memory, confirmations, and follow-up resolution
- the LLM focuses on natural conversation and deciding when tools are needed

This gives the project both conversational flexibility and deterministic domain behavior.

## Features

- tee-time search
- weather-aware recommendations
- default filtering for rain and wind above 20 km/h
- home area / travel mode / max travel time preferences
- reservation creation, hold, confirmation, and cancellation
- structured conversational memory
- Supabase Auth integration
- incremental migration toward Supabase Postgres + RLS

## Example User Experience

```text
User: nearest to adachi ku
Assistant: The nearest full course is Wakasu Golf Links.

User: tomorrow 12:00 3-4 players
Assistant: Confirms the date, time, course, player count, and weather before proceeding.

User: how will be the weather that day
Assistant: Reuses the active course/date/time from session context instead of asking again.

User: book the second one
Assistant: Resolves "the second one" against the previously presented tee-time options.
```

That behavior is intentional. The goal is to make the chatbot feel closer to a competent call-center agent than a stateless demo bot.

## URL Routing

The frontend now exposes stable page URLs:

- `/login`
- `/signup`
- `/assistant`
- `/tee-times`
- `/my-golf`
- `/settings`

## Local Development

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd frontend
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

At minimum, set:

- `OPENAI_API_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

### 3. Run

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

Docker support is included for both backend and frontend.

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Start everything with:

```bash
docker compose up --build
```

Exposed ports:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Notes:

- the frontend is served by Nginx and proxies `/chat`, `/auth`, `/api`, and `/health` to the backend service
- Supabase public env vars are baked into the frontend build, so set `NEXT_PUBLIC_...` values before building

## Supabase Migration Status

- `supabase/` is initialized
- initial schema:
  - `supabase/migrations/20260416183000_init_golf_reservation.sql`
- runtime additions:
  - `supabase/migrations/20260416190000_runtime_views_and_rls.sql`
- frontend uses Supabase Auth
- backend accepts Supabase JWTs
- some public read APIs prefer Supabase REST when configured

This is still an **incremental migration**, not a full cutover. Reservation-heavy MCP queries still mostly rely on SQLite today.

## Engineering Tradeoffs

- SQLite remains for fast local development and simple test setup
- Supabase Auth / Postgres / RLS were introduced early so the migration path is visible and reviewable
- explicit structured session state is used because prompt-only memory is not reliable enough for booking flows
- the migration strategy is intentionally incremental instead of rewriting everything at once

## If I Continued This Toward Production

1. Fully move reservation writes to Supabase Postgres.
2. Port remaining SQLite-specific MCP queries to Postgres-safe SQL.
3. Replace sample data with real course and pricing data.
4. Persist conversational state instead of keeping it in memory.
5. Add stronger observability, rate limiting, and background jobs.

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
