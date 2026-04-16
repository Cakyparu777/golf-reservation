# ⛳ Golf Reservation Chatbot

A conversational golf booking assistant built to demonstrate practical use of **MCP (Model Context Protocol)** in a real product flow.

The project combines:
- an **LLM host** that manages conversation state and tool orchestration
- a dedicated **MCP server** for golf-domain tools like tee-time search, booking, and weather-aware recommendations
- an incremental **Supabase migration** showing MCP + Auth + Postgres integration in a production-oriented direction

This is intentionally a portfolio-style project: the goal is not only to make the chatbot work, but to show recruiter-visible architecture decisions around tool use, structured memory, and backend integration.

## Tech Stack

- **Backend:** FastAPI, Python, MCP, OpenAI
- **Frontend:** React, TypeScript, Vite
- **Data:** SQLite today, Supabase Postgres migration in progress
- **Auth:** local JWT flow + Supabase Auth support
- **Infra direction:** Supabase, RLS, MCP-connected tooling

## Why I Built This

I wanted a project that shows more than prompt engineering.

This app is meant to demonstrate that I can build an AI product where:
- the LLM does not directly guess business data
- domain actions are routed through deterministic **MCP tools**
- conversation memory is handled explicitly instead of relying on raw chat history alone
- the system can evolve from local development architecture into a more production-ready stack with **Supabase Auth + Postgres**

In short, this project is designed to show that I can use MCP comfortably in a full-stack application, not just in isolated demos.

## What This Demonstrates

- **MCP-first thinking** — golf operations are exposed as tools instead of hidden inside prompts
- **LLM orchestration** — the host decides when to ask, confirm, call tools, and merge results back into the conversation
- **Structured memory** — follow-up phrases like `that day`, `there`, and `book the second one` are resolved with session context
- **Real integration work** — weather lookup, travel preferences, Supabase Auth, RLS, and Postgres migration planning are part of the app
- **Incremental engineering** — the codebase keeps working while moving from SQLite/local auth toward Supabase/Postgres

## Architecture

```
User → FastAPI (Host) → OpenAI LLM → MCP Client → MCP Server (FastMCP) → SQLite / Supabase-ready Postgres
```

The system uses a **Host ↔ MCP Server** architecture:
- **Host** (FastAPI): Receives user messages, orchestrates the LLM, and manages conversation state.
- **MCP Server** (FastMCP): Exposes 7 tools for searching tee times, managing reservations, and getting course info.
- **LLM** (OpenAI): Interprets natural language and decides which tools to call.
- **Database** (SQLite today, Supabase/Postgres in progress): Stores courses, tee times, users, and reservations.

## MCP In This Project

- The assistant uses an explicit **tool-calling workflow** instead of pretending to know booking data.
- Golf-specific operations are exposed through the local MCP server, so the LLM can call deterministic tools for:
  - tee-time search
  - reservation creation / confirmation / cancellation
  - course lookup
  - alternatives and recommendations
  - weather checks
- Supabase is also connected through MCP / OpenCode config so the project demonstrates comfort with remote MCP-backed workflows, not just local tool wiring.

## Architecture Decisions

- **Host + MCP split** — the FastAPI host handles chat state, confirmation logic, and orchestration; the MCP server handles golf-domain actions as focused tools
- **Deterministic workflow around the LLM** — the assistant can sound natural, but booking logic is guarded by explicit rules and structured context
- **Progressive migration strategy** — SQLite keeps local development simple while Supabase Auth and Postgres are added incrementally
- **Weather + travel constraints as product logic** — recommendations are filtered by practical constraints like rain, wind, location, and travel mode

## Features

- 🔍 **Search tee times** by date, time, course, and player count
- 📋 **Make reservations** with a 2-phase booking flow (PENDING → CONFIRMED)
- 🔄 **Suggest alternatives** when a slot is unavailable
- ❌ **Cancel reservations** with slot restoration
- 📊 **View bookings** by email with status filtering
- ℹ️ **Course info** with amenities, ratings, and contact details
- 🌦️ **Weather-aware recommendations** with default rain/wind filtering
- 👤 **Travel-profile preferences** for home area, travel mode, and max travel time
- 🧠 **Structured chat memory** for follow-ups like "that day", "there", or "book the second one"
- 🔐 **Supabase-ready auth and Postgres migration path** with RLS policies started

## Example User Experience

```text
User: nearest to adachi ku
Assistant: The nearest full course is Wakasu Golf Links.

User: tomorrow 12:00 3-4 players
Assistant: Confirms the date, time, course, player count, and weather before proceeding.

User: how will be the weather that day
Assistant: Reuses the active course/date/time from session context instead of asking again.

User: book the second one
Assistant: Resolves "the second one" against the last presented tee-time options.
```

That behavior is intentional: the goal is to make the chatbot feel closer to a competent call-center agent than a stateless demo bot.

## What Recruiters Should Notice

- the LLM is used for interpretation and response generation, not as the source of truth
- MCP tools handle domain actions in a transparent, inspectable way
- conversation reliability is improved with explicit session context and confirmation rules
- the project shows incremental migration work across auth, database, and infra instead of staying as a toy demo

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
# For Supabase frontend auth, also set either:
# - VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY
# or
# - NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

### 3. Run

```bash
# Option A: Use the start script
chmod +x scripts/start_server.sh
./scripts/start_server.sh --reload

# Option B: Run directly
python -m backend.db.seed_data
uvicorn backend.host.app:app --reload
```

### 4. Chat

```bash
# Send a message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me a tee time for 4 players tomorrow near Adachi-ku",
    "user_name": "John Doe",
    "user_email": "john@example.com"
  }'
```

API docs available at: http://localhost:8000/docs

## Testing

```bash
pytest tests/ -v
```

## Supabase Migration Status

- `supabase/` has been initialized and linked through MCP/OpenCode tooling.
- Initial Postgres schema lives in `supabase/migrations/20260416183000_init_golf_reservation.sql`.
- Runtime migration pieces now include:
  - `supabase/migrations/20260416190000_runtime_views_and_rls.sql` for public read views and RLS policies
  - frontend Supabase Auth wiring
  - backend acceptance of Supabase-issued JWTs
  - public course / tee-time API fallback to Supabase REST when configured
- The backend now accepts either local JWTs or Supabase Auth JWTs for protected API routes.
- The app still uses SQLite for the main runtime database today, so this is an incremental migration rather than a full cutover.

## Engineering Tradeoffs

- I kept **SQLite** for local speed and simple testing while building the domain logic
- I added **Supabase Auth + Postgres migration files** before fully cutting over runtime writes, so the migration path stays visible and reviewable
- I used **explicit session context** because prompt-only memory is not reliable enough for booking flows
- I prefer safe, incremental migration over rewriting everything at once and breaking the product

Recommended next migration steps:

1. Port the remaining SQLite-specific MCP queries to Postgres-safe SQL.
2. Switch reservation/chat runtime writes from SQLite to Supabase Postgres.
3. Seed or import real course / tee-time data into Supabase.
4. Tighten production RLS policies and split service-role operations from client operations.

## If I Continued This Toward Production

1. Move reservation creation/cancellation fully to Supabase Postgres.
2. Port remaining SQLite-specific MCP queries to Postgres-safe SQL.
3. Replace sample course data with real golf inventory and pricing feeds.
4. Add persistent conversation state storage instead of in-memory session state.
5. Add stronger observability, rate limiting, and background job handling.

## Project Structure

```
golf-reservation/
├── backend/
│   ├── mcp_server/          # MCP Server (FastMCP)
│   │   ├── server.py        # Tool registration & entry point
│   │   ├── tools/           # Tool implementations
│   │   │   ├── search.py    # search_tee_times, get_course_info, suggest_alternatives
│   │   │   ├── reservation.py # make, confirm, cancel
│   │   │   └── user.py      # list_user_reservations
│   │   └── db/              # Database layer
│   │       ├── connection.py # SQLite connection helper
│   │       ├── models.py    # Pydantic models
│   │       └── queries.py   # SQL constants
│   ├── host/                # FastAPI Host
│   │   ├── app.py           # Main app & /chat endpoint
│   │   ├── llm.py           # OpenAI wrapper & tool definitions
│   │   ├── mcp_client.py    # MCP client (stdio transport)
│   │   ├── conversation.py  # Session & history manager
│   │   └── schemas.py       # API schemas
│   └── db/
│       ├── init_db.py       # Schema creation
│       └── seed_data.py     # Sample data generator
├── tests/
├── scripts/
├── pyproject.toml
└── .env.example
```

## License

MIT
