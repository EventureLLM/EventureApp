from dotenv import load_dotenv
from datetime import datetime, timedelta

import os
import json
import openai
import requests

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ticketmaster_key = os.getenv("TICKETMASTER_API_KEY")

# Verify
print("OpenAI Key Found:", bool(os.getenv("OPENAI_API_KEY")))

MODEL_NAME = "gpt-4o-mini"
client = openai.OpenAI()

def makeTicketmasterEventRequest(params: dict):
    print(f"--- Calling Ticketmaster API with params: {params} ---")
    params['apikey'] = ticketmaster_key
    url = f'https://app.ticketmaster.com/discovery/v2/events.json'

    r = requests.get(url,params=params)
    print(f"--- Ticketmaster API Status Code: {r.status_code} ---")

    return r.text

def makeTicketmasterVenuesRequest(params: dict):
    print(f"--- Calling Ticketmaster API with params: {params} ---")
    params['apikey'] = ticketmaster_key
    url = f'https://app.ticketmaster.com/discovery/v2/venues.json'

    r = requests.get(url,params=params)
    print(f"--- Ticketmaster API Status Code: {r.status_code} ---")

    return r.text

function_descriptions = [
    {
        "type": "function",
        "function": {
            "name": "makeTicketmasterEventRequest",
            "description": "Fetches all events happening in a specific location from Ticketmaster.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search term for events, e.g., 'music', 'sports'."
                    },
                    "city": {
                        "type": "string",
                        "description": "The city to fetch events for, e.g., 'Detroit'."
                    },
                    "stateCode": {
                        "type": "string",
                        "description": "The state code, e.g., 'MI' for Michigan."
                    },
                    "countryCode": {
                        "type": "string",
                        "description": "The country code, e.g., 'US'."
                    },
                    "startDateTime": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Start date and time for events in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."
                    },
                    "endDateTime": {
                        "type": "string",
                        "format": "date-time",
                        "description": "End date and time for events in ISO 8601 format."
                    }
                },
                "required": ["city", "stateCode", "countryCode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "makeTicketmasterVenuesRequest",
            "description": "Get details for a specific venue using the unique identifier for the venue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search term for events, e.g., 'music', 'sports'."
                    },
                    "stateCode": {
                        "type": "string",
                        "description": "The state code, e.g., 'MI' for Michigan."
                    },
                    "countryCode": {
                        "type": "string",
                        "description": "The country code, e.g., 'US'."
                    },
                },
                "required": ["stateCode", "countryCode"]
            }
        }
    }
]

def test_call_model(user_message: str, function_call="auto"):
    """
    1) We send user_message + function_descriptions to the model
    2) We see if it returns a function call
    3) If so, we parse arguments, call the function ourselves
    4) Return final output
    """

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": user_message}],
        tools=function_descriptions,  # 'functions' is now called 'tools'
        tool_choice=function_call,    # 'function_call' is now 'tool_choice'
    )
    response = completion.choices[0].message
    return response

def run_conversation(user_prompt_1):
  messages = []
  messages.append({"role": "user", "content": user_prompt_1})

  response_message = test_call_model(user_prompt_1)
  messages.append(response_message.model_dump(exclude_unset=True))

  tool_calls = response_message.tool_calls
  
  available_functions = {
    "makeTicketmasterEventRequest": makeTicketmasterEventRequest,
    "makeTicketmasterVenuesRequest": makeTicketmasterVenuesRequest
    # we can add more functions here <--
  }

  tool_responses = []

  for tool_call in tool_calls:
    function_name = tool_call.function.name
    tool_call_id = tool_call.id

    function_to_call = available_functions[function_name]

    function_args = json.loads(tool_call.function.arguments)
    function_response_data = function_to_call(params=function_args)

    tool_responses.append(
        {
          "tool_call_id": tool_call_id,
          "role": "tool",
          "name": function_name,
          "content": function_response_data,
      }
    )

  messages.extend(tool_responses)

  second_response = client.chat.completions.create(
      model=MODEL_NAME,
      messages=messages,
  )
  final_response_message = second_response.choices[0].message
  messages.append(final_response_message.model_dump(exclude_unset=True))
  final_response_content = final_response_message.content

  return final_response_content, messages

def getAllEvents():
  answer, current_history = run_conversation(
    f"What events are going on April 6, 2025 in Detroit?",
  )
  return answer