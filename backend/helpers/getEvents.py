from dotenv import load_dotenv
from datetime import datetime

import os
import json
import openai
import requests

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ticketmaster_key = os.getenv("TICKETMASTER_API_KEY")

print("OpenAI Key Found:", bool(os.getenv("OPENAI_API_KEY")))

MODEL_NAME = "gpt-4o-mini"
client = openai.OpenAI()

SYSTEM_PROMPT = (
    "You are Eventure, a travel planning assistant that helps users discover events "
    "and venues in cities they plan to visit. When a user asks about events or venues "
    "in a location, use the available tools to fetch real-time data from Ticketmaster "
    "and present the results in a friendly, organized way. If the user's request does "
    "not involve finding events or venues — for example, if they ask a general travel "
    "question — answer helpfully without calling a tool. Always clarify with the user "
    "if you need a city or date to complete their request."
)


# ---------------------------------------------------------------------------
# Ticketmaster API helpers
# ---------------------------------------------------------------------------

def makeTicketmasterEventRequest(params: dict) -> str:
    print(f"--- Calling Ticketmaster Events API with params: {params} ---")
    params["apikey"] = ticketmaster_key
    r = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json",
        params=params,
    )
    print(f"--- Ticketmaster Events API status: {r.status_code} ---")
    return r.text


def makeTicketmasterVenuesRequest(params: dict) -> str:
    print(f"--- Calling Ticketmaster Venues API with params: {params} ---")
    params["apikey"] = ticketmaster_key
    r = requests.get(
        "https://app.ticketmaster.com/discovery/v2/venues.json",
        params=params,
    )
    print(f"--- Ticketmaster Venues API status: {r.status_code} ---")
    return r.text


AVAILABLE_FUNCTIONS = {
    "makeTicketmasterEventRequest": makeTicketmasterEventRequest,
    "makeTicketmasterVenuesRequest": makeTicketmasterVenuesRequest,
}

TOOL_DESCRIPTIONS = [
    {
        "type": "function",
        "function": {
            "name": "makeTicketmasterEventRequest",
            "description": "Fetches events happening in a specific location from Ticketmaster.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search term for events, e.g., 'music', 'sports'.",
                    },
                    "city": {
                        "type": "string",
                        "description": "The city to fetch events for, e.g., 'Detroit'.",
                    },
                    "stateCode": {
                        "type": "string",
                        "description": "Two-letter state code, e.g., 'MI' for Michigan.",
                    },
                    "countryCode": {
                        "type": "string",
                        "description": "Two-letter country code, e.g., 'US'.",
                    },
                    "startDateTime": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Start date/time in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).",
                    },
                    "endDateTime": {
                        "type": "string",
                        "format": "date-time",
                        "description": "End date/time in ISO 8601 format.",
                    },
                },
                "required": ["city", "stateCode", "countryCode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "makeTicketmasterVenuesRequest",
            "description": "Fetches venue details for a given location from Ticketmaster.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search term for venues, e.g., 'arena', 'theater'.",
                    },
                    "stateCode": {
                        "type": "string",
                        "description": "Two-letter state code, e.g., 'MI' for Michigan.",
                    },
                    "countryCode": {
                        "type": "string",
                        "description": "Two-letter country code, e.g., 'US'.",
                    },
                },
                "required": ["stateCode", "countryCode"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Core agent logic
# ---------------------------------------------------------------------------

def _execute_tool_calls(tool_calls: list) -> list[dict]:
    """Execute all tool calls returned by the model and return tool result messages."""
    tool_responses = []
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        tool_call_id = tool_call.id

        function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
        if function_to_call is None:
            # Unknown tool — return an error message so the model can recover
            tool_responses.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps({"error": f"Unknown function: {function_name}"}),
            })
            continue

        function_args = json.loads(tool_call.function.arguments)
        result = function_to_call(params=function_args)

        tool_responses.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": function_name,
            "content": result,
        })

    return tool_responses


def run_turn(user_message: str, history: list[dict]) -> tuple[str, list[dict]]:
    """
    Run a single conversational turn.

    Args:
        user_message: The latest message from the user.
        history:      The full conversation history so far (list of message dicts).
                      Pass an empty list to start a new conversation.

    Returns:
        (assistant_reply, updated_history)
        - assistant_reply: The final text response to show the user.
        - updated_history: The conversation history including this turn,
                           ready to pass back in on the next call.
    """
    # Build the full message list: system prompt + history + new user turn
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_message})

    # First model call — may return text or a tool call
    first_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=TOOL_DESCRIPTIONS,
        tool_choice="auto",
    )
    response_message = first_response.choices[0].message
    messages.append(response_message.model_dump(exclude_unset=True))

    tool_calls = response_message.tool_calls

    # --- Crash guard: if the model chose not to call a tool, return directly ---
    if not tool_calls:
        reply = response_message.content or ""
        # Persist the user turn + assistant reply into history (strip system prompt)
        updated_history = messages[1:]
        return reply, updated_history

    # Execute every tool call the model requested
    tool_responses = _execute_tool_calls(tool_calls)
    messages.extend(tool_responses)

    # Second model call — synthesize tool results into a natural language reply
    second_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    final_message = second_response.choices[0].message
    messages.append(final_message.model_dump(exclude_unset=True))

    reply = final_message.content or ""
    # Strip system prompt before returning so callers store only the dialogue
    updated_history = messages[1:]
    return reply, updated_history


# ---------------------------------------------------------------------------
# Convenience wrapper (used by app.py for the single-shot GET endpoint)
# ---------------------------------------------------------------------------

def getAllEvents(prompt: str = "What events are going on this weekend in Detroit?") -> str:
    reply, _ = run_turn(prompt, history=[])
    return reply
