# ⛳ Golf Reservation Chatbot

A conversational chatbot for booking golf tee times, powered by **MCP (Model Context Protocol)** and **OpenAI**.

## Architecture

```
User → FastAPI (Host) → OpenAI LLM → MCP Client → MCP Server (FastMCP) → SQLite
```

The system uses a **Host ↔ MCP Server** architecture:
- **Host** (FastAPI): Receives user messages, orchestrates the LLM, and manages conversation state.
- **MCP Server** (FastMCP): Exposes 7 tools for searching tee times, managing reservations, and getting course info.
- **LLM** (OpenAI): Interprets natural language and decides which tools to call.
- **Database** (SQLite): Stores courses, tee times, users, and reservations.

## Features

- 🔍 **Search tee times** by date, time, course, and player count
- 📋 **Make reservations** with a 2-phase booking flow (PENDING → CONFIRMED)
- 🔄 **Suggest alternatives** when a slot is unavailable
- ❌ **Cancel reservations** with slot restoration
- 📊 **View bookings** by email with status filtering
- ℹ️ **Course info** with amenities, ratings, and contact details

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
    "message": "Find me a tee time for 4 players this Saturday morning at Pebble Beach",
    "user_name": "John Doe",
    "user_email": "john@example.com"
  }'
```

API docs available at: http://localhost:8000/docs

## Testing

```bash
pytest tests/ -v
```

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
