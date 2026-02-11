"""
Conversational Chat Agent for Browser Automation.

This module provides a Gemini-powered conversational agent that:
- Parses natural language requests (e.g., "book a flight for 2 from Delhi to Mumbai")
- Asks intelligent follow-up questions for missing details
- Triggers browser automation when all details are collected
- Handles both flight booking and general automation tasks
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from google.genai.types import Content, Part

from config import client


# =============================================================================
# System Prompt
# =============================================================================

CHAT_SYSTEM_PROMPT = """You are a friendly AI travel assistant and browser automation agent. You help users book flights and automate browser tasks.

## FLIGHT BOOKING MODE
When a user wants to book a flight, extract details from their message and ask follow-up questions for anything missing.

Required details for flight booking:
1. **origin** — Departure city (e.g., "Delhi", "Mumbai")
2. **destination** — Arrival city (e.g., "Goa", "Bangalore")
3. **departure_date** — Date of travel (parse natural language: "tomorrow", "next Monday", "5th Nov", etc.)
4. **trip_type** — "one-way" or "round-trip" (ASK if not mentioned)
5. **return_date** — Only if round-trip (ASK if they say round-trip)
6. **passengers** — Number of adults, children, infants (default: 1 adult if not mentioned)
7. **class** — economy, premium_economy, business, first (default: economy if not mentioned)
8. **time_preference** — morning, afternoon, evening, night, any (default: any)
9. **booking_site** — The airline website domain for sign-in (e.g., "airindia.com", "goindigo.in", "spicejet.com"). Default: "airindia.com". Ask the user which airline they prefer if they mention a specific one.

## CONVERSATION RULES
1. Be conversational and friendly, use emojis occasionally
2. Extract as much as possible from the first message
3. Ask follow-up questions ONE AT A TIME — don't overwhelm with all questions at once
4. When you have enough info, CONFIRM the details with the user before booking
5. If user says something vague like "book a flight", ask where they want to go
6. Always parse dates relative to today's date: {today}

## RESPONSE FORMAT
You MUST respond with valid JSON in this exact format:

For conversation responses (asking questions, confirming, chatting):
```json
{{"type": "message", "text": "Your message to the user"}}
```

For confirming booking details (show summary and ask for confirmation):
```json
{{"type": "confirm", "text": "Here's your booking summary:\\n\\n✈️ Delhi → Mumbai\\n📅 5th Nov 2026\\n👥 2 Adults\\n💺 Economy\\n\\nShall I go ahead and book this?", "booking_details": {{"origin": "Delhi", "destination": "Mumbai", "departure_date": "2026-11-05", "trip_type": "one-way", "passengers": {{"adults": 2, "children": 0, "infants": 0}}, "class": "economy", "time_preference": "any", "flexible_dates": 0, "booking_site": "airindia.com"}}}}
```

For triggering automation after user confirms:
```json
{{"type": "action", "action": "book_flight", "text": "Great! Let me book that for you. Opening the browser now... 🚀", "booking_details": {{"origin": "Delhi", "destination": "Mumbai", "departure_date": "2026-11-05", "trip_type": "one-way", "passengers": {{"adults": 2, "children": 0, "infants": 0}}, "class": "economy", "time_preference": "any", "flexible_dates": 0, "booking_site": "airindia.com"}}}}
```

For general browser automation (non-flight tasks):
```json
{{"type": "action", "action": "automate", "text": "Sure, let me do that for you! 🤖", "goal": "Search for Python tutorials on Google"}}
```

## IMPORTANT
- ALWAYS respond with JSON only, no markdown or extra text
- Parse dates intelligently: "tomorrow" = {tomorrow}, "next week" = {next_week}
- If user confirms booking (says yes, sure, go ahead, etc.), respond with type "action"
- If user says no or wants to change something, ask what they'd like to change
- For non-flight requests like "search for X" or "open Y website", use the general automation action
"""


# =============================================================================
# Chat Agent
# =============================================================================

class ChatAgent:
    """
    Conversational AI agent powered by Gemini.
    
    Maintains conversation history and intelligently guides users
    through flight booking or general automation tasks.
    """
    
    MODEL = "gemini-2.5-flash"
    
    def __init__(self):
        """Initialize the chat agent."""
        self.conversation_history: List[Dict[str, str]] = []
        self.state = "idle"  # idle, collecting, confirming, automating
        self.pending_booking: Optional[Dict] = None
        self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with current date context."""
        today = datetime.now()
        self.system_prompt = CHAT_SYSTEM_PROMPT.format(
            today=today.strftime("%A, %B %d, %Y"),
            tomorrow=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
            next_week=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
        )
    
    def reset(self):
        """Reset conversation state."""
        self.conversation_history = []
        self.state = "idle"
        self.pending_booking = None
        self._build_system_prompt()
    
    def chat(self, user_message: str) -> Dict:
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The user's chat message
            
        Returns:
            Dict with keys: type, text, and optionally booking_details/goal
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "text": user_message,
        })
        
        # Build Gemini request
        contents = self._build_contents(user_message)
        
        try:
            response = client.models.generate_content(
                model=self.MODEL,
                contents=contents,
            )
            
            response_text = response.text.strip()
            parsed = self._parse_response(response_text)
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "text": parsed.get("text", ""),
                "raw": response_text,
            })
            
            # Update state based on response type
            if parsed["type"] == "confirm":
                self.state = "confirming"
                self.pending_booking = parsed.get("booking_details")
            elif parsed["type"] == "action":
                self.state = "automating"
            elif parsed["type"] == "message":
                if self.state != "confirming":
                    self.state = "collecting"
            
            return parsed
            
        except Exception as e:
            error_response = {
                "type": "message",
                "text": f"Sorry, I ran into an issue: {str(e)}. Could you try again?",
            }
            self.conversation_history.append({
                "role": "assistant",
                "text": error_response["text"],
            })
            return error_response
    
    def _build_contents(self, user_message: str) -> List[Content]:
        """Build the full conversation contents for Gemini."""
        contents = []
        
        # System prompt as first user message
        contents.append(Content(
            role="user",
            parts=[Part(text=self.system_prompt)],
        ))
        contents.append(Content(
            role="model",
            parts=[Part(text='{"type": "message", "text": "Hi! I\'m your AI travel assistant. I can help you book flights or automate browser tasks. What would you like to do? ✈️🤖"}')],
        ))
        
        # Add conversation history (skip the current message, we add it separately)
        for msg in self.conversation_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            text = msg.get("raw", msg["text"]) if role == "model" else msg["text"]
            contents.append(Content(
                role=role,
                parts=[Part(text=text)],
            ))
        
        # Add current user message
        contents.append(Content(
            role="user",
            parts=[Part(text=user_message)],
        ))
        
        return contents
    
    def _parse_response(self, response_text: str) -> Dict:
        """
        Parse the JSON response from Gemini.
        
        Handles cases where Gemini wraps JSON in markdown code blocks.
        """
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.strip()
        
        try:
            parsed = json.loads(text)
            
            # Validate required fields
            if "type" not in parsed:
                parsed["type"] = "message"
            if "text" not in parsed:
                parsed["text"] = "I'm not sure how to respond to that. Could you rephrase?"
            
            return parsed
            
        except json.JSONDecodeError:
            # If Gemini returns plain text instead of JSON, wrap it
            return {
                "type": "message",
                "text": text,
            }
    
    def get_greeting(self) -> Dict:
        """Return the initial greeting message."""
        return {
            "type": "message",
            "text": "Hey there! 👋 I'm your AI assistant. I can help you:\n\n✈️ **Book flights** — Just tell me where you want to go!\n🤖 **Automate browser tasks** — Tell me what to search, open, or do.\n\nTry something like: *\"Book a flight for 2 from Delhi to Mumbai on 5th Nov\"*",
        }
