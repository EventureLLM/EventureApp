# Eventure

An AI-powered travel planning agent that helps users discover events and venues in cities they plan to visit. Users describe what they're looking for in natural language — Eventure's backend agent decides which Ticketmaster API tools to invoke, fetches real-time data, and returns a synthesized, human-readable response.

---

## Architecture

Eventure is built around an **agentic workflow** that combines deterministic and generative components:

```
User message
     │
     ▼
GPT-4o-mini (tool-calling)
     │
     ├── decides to call → makeTicketmasterEventRequest(city, date, keyword, ...)
     │                             │
     │                             ▼
     │                     Ticketmaster Discovery API
     │                             │
     │                             ▼  (raw JSON response)
     └── or calls → makeTicketmasterVenuesRequest(stateCode, ...)
                                   │
                                   ▼
                     GPT-4o-mini (synthesis turn)
                                   │
                                   ▼
                         Natural language reply
```

The model autonomously selects which tool(s) to call and extracts structured API parameters directly from natural language. If the user's request doesn't require a tool call (e.g., a general travel question), the model responds directly without hitting any external API.

Conversation history is maintained across turns via a `session_id`, enabling genuine multi-turn interactions — a user can ask a follow-up like "what about venues near there?" and the agent understands the prior context.

---

## Tech stack

| Layer | Technology |
|---|---|
| Agent / LLM | OpenAI `gpt-4o-mini` (tool calling) |
| External data | Ticketmaster Discovery API v2 |
| Backend | Python, Flask, flask-restful, flask-cors |
| Config | python-dotenv |

---

## Getting started

### 1. Clone and install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set up environment variables

Create a `.env` file in `backend/`:

```
OPENAI_API_KEY=sk-...
TICKETMASTER_API_KEY=...
FLASK_SECRET_KEY=some-random-string
```

### 3. Run the server

```bash
cd backend
python app.py
```

The server starts at `http://127.0.0.1:5000`.

---

## API reference

### `GET /`
Single-shot demo. Returns a sample event query for Detroit with no session required.

**Response:**
```json
{ "response": "Here are some events happening this weekend in Detroit..." }
```

---

### `POST /chat`
Multi-turn conversational endpoint.

**Request body:**
```json
{
  "message": "What music events are happening in Chicago next weekend?",
  "session_id": "optional-uuid-from-previous-turn"
}
```

**Response:**
```json
{
  "reply": "Here are some music events in Chicago next weekend...",
  "session_id": "uuid-to-pass-on-next-turn"
}
```

Pass the returned `session_id` back on every subsequent message to maintain conversation context. Omit it (or send a new one) to start a fresh conversation.

**Example multi-turn exchange:**
```
User:  "What events are in Austin this weekend?"
Agent: "Here are 5 events in Austin this weekend: ..."

User:  "Are there any country music ones specifically?"
Agent: "From those results, two are country: ..."   ← agent uses prior context
```

---

### `DELETE /chat/<session_id>`
Clears the conversation history for a given session.

---

## Project status

The backend agent is functional: tool routing, API integration, and multi-turn conversation history are all working. The frontend (React/Vite scaffold in `frontend/`) is not yet connected to the backend.

---

## Potential next steps

- Connect the React frontend to the `/chat` endpoint
- Persist conversation history to a database (SQLite or Redis) instead of in-memory
- Add support for additional Ticketmaster endpoints (attractions, classifications)
- Deploy backend to Render or Railway; frontend to Vercel
