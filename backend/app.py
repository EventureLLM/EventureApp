from flask import Flask, jsonify, request, session
from flask_restful import Api
from flask_cors import CORS

import os
import uuid

from helpers.getEvents import run_turn, getAllEvents

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
CORS(app, supports_credentials=True)
api = Api(app)

# In-memory store mapping session_id -> conversation history.
# A production version would persist this to a database.
_conversations: dict[str, list[dict]] = {}


@app.route("/", methods=["GET"])
def index():
    """Single-shot demo endpoint — no session required."""
    response = getAllEvents()
    return jsonify({"response": response})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Multi-turn conversational endpoint.

    Request body (JSON):
        {
            "message":    "<user message>",      # required
            "session_id": "<uuid string>"        # optional — omit to start a new conversation
        }

    Response (JSON):
        {
            "reply":      "<assistant reply>",
            "session_id": "<uuid string>"        # pass this back on every subsequent turn
        }
    """
    body = request.get_json(force=True, silent=True) or {}
    user_message = body.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Missing 'message' in request body."}), 400

    # Resolve or create a session
    session_id = body.get("session_id") or str(uuid.uuid4())
    history = _conversations.get(session_id, [])

    reply, updated_history = run_turn(user_message, history)

    # Persist updated history
    _conversations[session_id] = updated_history

    return jsonify({"reply": reply, "session_id": session_id})


@app.route("/chat/<session_id>", methods=["DELETE"])
def clear_conversation(session_id: str):
    """Clear the conversation history for a given session."""
    _conversations.pop(session_id, None)
    return jsonify({"status": "cleared", "session_id": session_id})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
