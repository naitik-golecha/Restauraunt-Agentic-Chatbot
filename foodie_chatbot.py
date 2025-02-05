import streamlit as st

import json

import requests

from datetime import datetime

# Load restaurant data

with open('data/restaurants.json') as f:

    restaurants = json.load(f)

# Groq API settings

GROQ_API_KEY = "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"

GROQ_URL = "https://api.groq.com/v1/chat/completions"

def query_llm(messages, tools=None):

    headers = {

        "Authorization": f"Bearer {GROQ_API_KEY}",

        "Content-Type": "application/json"

    }

    payload = {

        "model": "llama-3.1-8b-instant",

        "messages": messages,

        "temperature": 0.7,

        "tools": tools,

        "tool_choice": "auto" if tools else None

    }

    response = requests.post(GROQ_URL, json=payload, headers=headers)

    return response.json()

# Tool definitions

tools = [

    {

        "type": "function",

        "function": {

            "name": "find_restaurants",

            "description": "Find restaurants based on criteria",

            "parameters": {

                "type": "object",

                "properties": {

                    "cuisine": {"type": "string"},

                    "location": {"type": "string"},

                    "party_size": {"type": "integer"},

                    "time": {"type": "string"}

                }

            }

        }

    },

    {

        "type": "function",

        "function": {

            "name": "make_reservation",

            "description": "Make a restaurant reservation",

            "parameters": {

                "type": "object",

                "properties": {

                    "restaurant_id": {"type": "integer"},

                    "time": {"type": "string"},

                    "party_size": {"type": "integer"},

                    "date": {"type": "string"}

                },

                "required": ["restaurant_id", "time", "party_size", "date"]

            }

        }

    }

]

# Tool implementations

def find_restaurants(cuisine=None, location=None, party_size=None, time=None):

    filtered = restaurants

    if cuisine:

        filtered = [r for r in filtered if r['cuisine'].lower() == cuisine.lower()]

    if location:

        filtered = [r for r in filtered if r['location'].lower() == location.lower()]

    # Add availability check

    if time and party_size:

        filtered = [r for r in filtered if check_availability(r, time, party_size)]

    return filtered[:5]  # Return top 5 results

def make_reservation(restaurant_id, time, party_size, date):

    restaurant = next(r for r in restaurants if r['id'] == restaurant_id)

    if check_availability(restaurant, time, party_size, date):

        # Update availability

        key = f"{date} {time}"

        restaurant['available_slots'][date][time] -= party_size

        return {"status": "confirmed", "restaurant": restaurant['name']}

    return {"status": "failed"}

def check_availability(restaurant, time, party_size, date):

    return restaurant['available_slots'].get(date, {}).get(time, 0) >= party_size

# Streamlit UI

st.title("FoodieSpot Assistant")

if "messages" not in st.session_state:

    st.session_state.messages = [{

        "role": "assistant",

        "content": "Hi! I'm your FoodieSpot assistant. How can I help you today?"

    }]

for msg in st.session_state.messages:

    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():

    st.session_state.messages.append({"role": "user", "content": prompt})

    st.chat_message("user").write(prompt)

    # Get LLM response

    response = query_llm(st.session_state.messages, tools)

    # Process tool calls

    if "tool_calls" in response['choices'][0]['message']:

        for tool_call in response['choices'][0]['message']['tool_calls']:

            func_name = tool_call['function']['name']

            args = json.loads(tool_call['function']['arguments'])

            if func_name == "find_restaurants":

                results = find_restaurants(**args)

                # Format results for display

                response_text = "\n".join([f"{r['name']} ({r['cuisine']}) in {r['location']}" for r in results])

            elif func_name == "make_reservation":

                result = make_reservation(**args)

                response_text = f"Reservation {result['status']} at {result['restaurant']}"

            st.session_state.messages.append({

                "role": "assistant",

                "content": response_text

            })

    else:

        response_text = response['choices'][0]['message']['content']

        st.session_state.messages.append({

            "role": "assistant",

            "content": response_text

        })

    st.chat_message("assistant").write(response_text) 