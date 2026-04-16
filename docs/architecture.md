# Fairway Elite — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       FAIRWAY ELITE                             │
│                  Golf Reservation Platform                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND  (Vite dev: localhost:5173)               │
│           React 18 + TypeScript + Vite + Tailwind               │
│                                                                 │
│  Context Providers (wrap entire app)                            │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐    │
│  │  AuthContext  │  │  ChatContext  │  │   ToastContext    │    │
│  │ Supabase auth │  │ messages +    │  │ global notifs    │    │
│  │ token + user  │  │ sessionID in  │  └──────────────────┘    │
│  │ profile       │  │ sessionStorage│                           │
│  └──────┬────────┘  └──────┬────────┘                          │
│         │                  │                                    │
│  ┌──────▼──────────────────▼──────────────────────────────┐    │
│  │               Pages (react-router-dom v7)               │    │
│  │                                                         │    │
│  │  /login       LoginPage     supabase.signInWithPassword │    │
│  │  /signup      SignupPage    supabase.signUp + PATCH /me │    │
│  │  /assistant   AssistantPage chat UI via ChatContext     │    │
│  │  /tee-times   TeeTimesPage  courses + weather + recs    │    │
│  │  /my-golf     MyGolfPage    reservations list           │    │
│  │  /settings    SettingsPage  home_area/travel/mode edit  │    │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  lib/: supabase.ts  api.ts  currency.ts  weather.ts  recs.ts   │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP (Vite proxy → localhost:8000)
                         │ /chat   /auth   /api   /health
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                BACKEND  (localhost:8000)                        │
│                   FastAPI + Python                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    REST API Routes                        │  │
│  │                                                          │  │
│  │  POST  /auth/register   create user + JWT               │  │
│  │  POST  /auth/login      verify password + JWT           │  │
│  │  GET   /auth/me         return profile                  │  │
│  │  PATCH /auth/me         update home_area/travel/mode    │  │
│  │                                                          │  │
│  │  GET   /api/courses     list courses                    │  │
│  │  GET   /api/tee-times   search future slots only        │  │
│  │  GET   /api/reservations   user's bookings  [JWT]       │  │
│  │  POST  /api/reservations   book + auto-confirm  [JWT]   │  │
│  │  DELETE /api/reservations/{id}  cancel  [JWT]           │  │
│  │                                                          │  │
│  │  POST  /chat            AI chatbot endpoint             │  │
│  │  GET   /health          status check                    │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                  /chat Orchestrator                       │  │
│  │                                                           │  │
│  │  1. Receive {message, session_id, user_name, user_email} │  │
│  │  2. Inject identity + current datetime into system msg   │  │
│  │  3. Call GPT-4o with 7 tool definitions                  │  │
│  │  4. If tool_call → dispatch to MCP Client                │  │
│  │  5. Add tool result → loop (max 5 rounds)                │  │
│  │  6. Return final reply + session_id                      │  │
│  └───────────┬────────────────────────┬──────────────────────┘  │
│              │                        │                          │
│    ┌─────────▼──────┐    ┌────────────▼──────────────┐          │
│    │  OpenAI SDK    │    │       MCP Client           │          │
│    │  GPT-4o        │    │  spawns subprocess via     │          │
│    │  function      │    │  sys.executable -m         │          │
│    │  calling       │    │  backend.mcp_server.server │          │
│    └────────────────┘    └────────────┬───────────────┘          │
└───────────────────────────────────────┼──────────────────────────┘
                                        │ JSON-RPC over stdin/stdout
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│               MCP SERVER  (stdio subprocess)                    │
│                  FastMCP + Python tools                         │
│                                                                 │
│  search_tee_times        future slots only (clamps to now)      │
│  get_course_info         course details + amenities             │
│  suggest_alternatives    nearby courses or different times      │
│  make_reservation        INSERT → status: PENDING              │
│  confirm_reservation     UPDATE → CONFIRMED + conf# FE-XXXXXX  │
│  cancel_reservation      UPDATE → CANCELLED + restore slot      │
│  list_user_reservations  SELECT by user email                   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ SQL
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              SQLite  data/golf_reservation.db                   │
│                                                                 │
│  golf_courses          5 courses                                │
│  tee_times             3600 rows (30 days × 5 × 24 slots)      │
│  users                 profiles + home_area/travel_mode         │
│  reservations          bookings with status + conf#             │
│  reservation_history   audit log of all status changes          │
└─────────────────────────────────────────────────────────────────┘
```

## Auth Flow

```
  No SUPABASE_URL env  →  local HS256 JWT (python-jose)
  SUPABASE_URL set     →  Supabase RS256 JWT via JWKS

  Login:
    supabase.signInWithPassword()
    → GET /auth/me (Supabase token)
    → backend upserts local user profile in SQLite/Supabase
    → returns AuthUser {id, name, email, home_area, travel_mode, max_travel_minutes}
```

## Chat Data Flow

```
  User types
    → ChatContext.sendMessage()
    → POST /chat {message, session_id, user_name, user_email}
    → system prompt stamped with identity + current datetime
    → GPT-4o decides: reply or call tool
    → tool call → MCP subprocess → SQL → JSON result
    → GPT-4o formats natural language reply
    → reply stored in sessionStorage
    → persists across page navigation, clears on tab close
```

## Key Design Decisions

| Concern | Decision |
|---|---|
| Chat persistence | `sessionStorage` — survives navigation, not tab close |
| Auth | Dual-mode: Supabase JWKS or local HS256 |
| MCP transport | stdio subprocess (started at app startup, not per request) |
| Past tee times | Clamped in both MCP tool and system prompt |
| DB | SQLite WAL for local dev; Supabase REST for production |
| Currency | All prices formatted as JPY |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Routing | react-router-dom v7 |
| Auth (frontend) | @supabase/supabase-js |
| Backend | FastAPI, Python |
| Auth (backend) | python-jose (HS256) + Supabase JWKS (RS256) |
| Password hashing | passlib + bcrypt 4.0.1 |
| AI | OpenAI GPT-4o (function calling) |
| MCP | FastMCP (stdio subprocess) |
| Database | SQLite (WAL mode) / Supabase PostgreSQL |
