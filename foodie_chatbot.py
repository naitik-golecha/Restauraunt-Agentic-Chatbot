import streamlit as st
import json
import requests
from datetime import datetime

# Initialize session state
if 'messages' not in st.session_state:
    # Add a system message to guide the assistant's behavior
    st.session_state['messages'] = [
        {
            "role": "system",
            "content": """You are a helpful restaurant booking assistant. When users ask about restaurants:
            1. If they mention cuisine, location, party size, or time, use the find_restaurants function
            2. If they want to make a booking, use the make_reservation function
            3. Always ask for missing information needed to help them
            4. Be conversational but focused on helping users find and book restaurants"""
        },
        {
            "role": "assistant",
            "content": "Hi! I'm your FoodieSpot assistant. I can help you find restaurants and make reservations. What kind of restaurant are you looking for?"
        }
    ]

# Load restaurant data
try:
    with open('data/restaurants.json') as f:
        restaurants = json.load(f)
except FileNotFoundError:
    st.error("restaurants.json file not found in data directory")
    restaurants = []

# Groq API settings
GROQ_API_KEY = ""
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def query_llm(messages, tools=None):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",  # Updated to use a supported model
            "messages": messages,
            "temperature": 0.7,
            "function_call": "auto",  # Updated function calling format
            "functions": tools if tools else None  # Updated to use 'functions' instead of 'tools'
        }
        response = requests.post(GROQ_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("Failed to decode API response")
        return None

# Updated tool definitions to match OpenAI function calling format
tools = [
    {
        "name": "find_restaurants",
        "description": "Find restaurants based on cuisine, location, party size, and time preferences",
        "parameters": {
            "type": "object",
            "properties": {
                "cuisine": {
                    "type": "string",
                    "description": "Type of cuisine (e.g., Italian, Japanese, Indian)"
                },
                "location": {
                    "type": "string",
                    "description": "Area or neighborhood"
                },
                "party_size": {
                    "type": "integer",
                    "description": "Number of people"
                },
                "time": {
                    "type": "string",
                    "description": "Preferred dining time (e.g., '19:00')"
                }
            }
        }
    },
    {
        "name": "make_reservation",
        "description": "Make a restaurant reservation",
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_id": {
                    "type": "integer",
                    "description": "ID of the restaurant"
                },
                "time": {
                    "type": "string",
                    "description": "Reservation time (e.g., '19:00')"
                },
                "party_size": {
                    "type": "integer",
                    "description": "Number of people"
                },
                "date": {
                    "type": "string",
                    "description": "Reservation date (YYYY-MM-DD)"
                }
            },
            "required": ["restaurant_id", "time", "party_size", "date"]
        }
    }
]

def find_restaurants(cuisine=None, location=None, party_size=None, time=None):
    filtered = restaurants
    if cuisine:
        filtered = [r for r in filtered if r['cuisine'].lower() == cuisine.lower()]
    if location:
        filtered = [r for r in filtered if r['location'].lower() == location.lower()]
    if time and party_size:
        filtered = [r for r in filtered if check_availability(r, time, party_size)]
    return filtered[:5]

def make_reservation(restaurant_id, time, party_size, date):
    try:
        restaurant = next(r for r in restaurants if r['id'] == restaurant_id)
        if check_availability(restaurant, time, party_size, date):
            key = f"{date} {time}"
            restaurant['available_slots'][date][time] -= party_size
            return {"status": "confirmed", "restaurant": restaurant['name']}
        return {"status": "failed", "reason": "No availability"}
    except StopIteration:
        return {"status": "failed", "reason": "Restaurant not found"}

def check_availability(restaurant, time, party_size, date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return restaurant['available_slots'].get(date, {}).get(time, 0) >= party_size

# Streamlit UI
st.title("FoodieSpot Assistant")

# Display chat messages
for msg in st.session_state.messages:
    if msg["role"] != "system":  # Don't display system messages
        st.chat_message(msg["role"]).write(msg["content"])

# Handle user input
if prompt := st.chat_input():
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Get LLM response
    response = query_llm(st.session_state.messages, tools)
    
    if response is None:
        error_message = "Sorry, I encountered an error while processing your request. Please try again."
        st.session_state.messages.append({
            "role": "assistant",
            "content": error_message
        })
        st.chat_message("assistant").write(error_message)
    else:
        try:
            if "choices" in response and len(response["choices"]) > 0:
                message = response["choices"][0].get("message", {})
                
                if "function_call" in message:  # Updated to use function_call instead of tool_calls
                    func_name = message["function_call"]["name"]
                    args = json.loads(message["function_call"]["arguments"])
                    
                    if func_name == "find_restaurants":
                        results = find_restaurants(**args)
                        if results:
                            response_text = "I found these restaurants for you:\n\n" + "\n".join(
                                [f"• {r['name']} ({r['cuisine']}) in {r['location']}" for r in results]
                            )
                        else:
                            response_text = "I couldn't find any restaurants matching your criteria. Would you like to try different options?"
                    elif func_name == "make_reservation":
                        result = make_reservation(**args)
                        if result["status"] == "confirmed":
                            response_text = f"Great! I've confirmed your reservation at {result['restaurant']}."
                        else:
                            response_text = f"Sorry, I couldn't make the reservation. {result.get('reason', 'Please try different options.')}"
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    st.chat_message("assistant").write(response_text)
                else:
                    response_text = message.get("content", "I apologize, but I couldn't process your request properly.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    st.chat_message("assistant").write(response_text)
            else:
                error_message = "I apologize, but I received an invalid response from the server."
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })
                st.chat_message("assistant").write(error_message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })
            st.chat_message("assistant").write(error_message)
