"""
Flight Booking Workflow Automation.

Interactive workflow: searches flights, then asks the user via chat
which flight to select (sends screenshot + description of options).
"""

import time
import base64
from typing import Callable, Dict, Optional

from playwright.sync_api import Page, sync_playwright
from google.genai.types import Content, Part

from config import client, get_generate_config, MODEL_NAME, SCREEN_WIDTH, SCREEN_HEIGHT
from utils.actions import execute_function_calls, get_function_responses
from utils.helpers import print_header


class FlightBookingWorkflow:
    """Automated flight booking workflow with user-in-the-loop selection."""

    def __init__(self, booking_details: Dict, ask_user_fn: Callable = None):
        """
        Args:
            booking_details: Dict with origin, destination, dates, etc.
            ask_user_fn: Callback to ask user a question via chat.
                         Signature: ask_user_fn(question, screenshot_b64) -> str
        """
        self.booking_details = booking_details
        self.ask_user_fn = ask_user_fn
        self.page: Optional[Page] = None
        self.browser = None
        self.playwright = None

    def execute(self):
        """Execute the complete flight booking workflow."""
        print_header("🚀 Starting Flight Booking Automation")
        d = self.booking_details
        print(f"   ✈️  {d.get('origin', '?')} → {d.get('destination', '?')}")
        print(f"   📅  {d.get('departure_date', '?')}")

        try:
            self._launch_browser()
            self._navigate_to_booking_site()
            self._fill_search_form()
            self._wait_for_results()
            self._ask_user_to_pick_flight()
            self._proceed_to_booking()
            self._handoff_payment()

            # Keep browser open for user to complete payment
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self._cleanup()

    def _launch_browser(self):
        print("🌐 Launching browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False, args=["--start-maximized"],
        )
        context = self.browser.new_context(
            viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
        )
        self.page = context.new_page()

    def _navigate_to_booking_site(self):
        print("📍 Navigating to Google Flights...")
        self.page.goto("https://www.google.com/travel/flights")
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

    def _fill_search_form(self):
        """Fill the search form using Gemini Computer Use."""
        print("📝 Filling search form...")
        d = self.booking_details

        screenshot = self.page.screenshot(type="png")
        config = get_generate_config()

        task = self._build_search_task()

        prompt = f"""You are controlling a browser on Google Flights.

TASK: Fill the flight search form with these details:
{task}

CRITICAL INSTRUCTIONS:

1. ORIGIN: Click the departure field → type "{d['origin']}" → WAIT for dropdown → CLICK the correct airport suggestion
2. DESTINATION: Click the destination field → type "{d['destination']}" → WAIT for dropdown → CLICK the correct airport suggestion  
3. DATES: Click date field → navigate to correct month → click the date {d['departure_date']}
   {"→ also select return date: " + d.get('return_date', '') if d.get('trip_type') == 'round-trip' else ''}
   → click Done
4. PASSENGERS: Set to {d.get('passengers', {}).get('adults', 1)} adult(s)
5. CLASS: Set to {d.get('class', 'economy')}
6. After filling, click the SEARCH button.

IMPORTANT: After typing origin/destination, WAIT for autocomplete suggestions and CLICK the right one. Don't just type and move on."""

        parts = [Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")]
        contents = [Content(role="user", parts=parts)]

        for turn in range(20):
            print(f"  🤖 Turn {turn + 1}...")

            response = client.models.generate_content(
                model=MODEL_NAME, contents=contents, config=config,
            )

            candidate = response.candidates[0]
            contents.append(candidate.content)

            fn_calls = [
                p.function_call for p in candidate.content.parts
                if hasattr(p, "function_call") and p.function_call
            ]

            if not fn_calls:
                print("  ✓ Form filled, search triggered")
                break

            results = execute_function_calls(candidate, self.page)
            func_responses, screenshot = get_function_responses(self.page, results)

            resp_parts = [Part(function_response=fr) for fr in func_responses]
            if screenshot:
                resp_parts.append(Part.from_bytes(data=screenshot, mime_type="image/png"))
            contents.append(Content(role="user", parts=resp_parts))
            time.sleep(0.5)

    def _wait_for_results(self):
        print("⏳ Waiting for results to load...")
        time.sleep(5)
        print("  ✓ Results loaded")

    def _ask_user_to_pick_flight(self):
        """
        Take a screenshot of flight results, use Gemini to describe
        the options, then ask the user which one they want via chat.
        """
        print("✈️ Analyzing flight options...")

        screenshot_bytes = self.page.screenshot(type="png")
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Use Gemini to describe the visible flight options
        describe_prompt = """Look at this flight search results page.
        
List ALL visible flight options as a numbered list with these details for each:
- Flight number / airline
- Departure time → Arrival time
- Duration
- Number of stops (nonstop / 1 stop / etc.)
- Price

Format as a clean numbered list like:
1. IndiGo 6E-123 | 06:15 → 08:30 | 2h 15m | Nonstop | ₹4,500
2. Air India AI-456 | 09:00 → 11:30 | 2h 30m | Nonstop | ₹5,200
...

Be accurate — read the actual values from the screenshot."""

        describe_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[Content(
                role="user",
                parts=[
                    Part(text=describe_prompt),
                    Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                ],
            )],
        )

        flight_list = describe_response.text.strip()
        print(f"  Found flights:\n{flight_list}")

        # Ask user via chat
        if self.ask_user_fn:
            question = (
                f"Here are the available flights I found:\n\n"
                f"{flight_list}\n\n"
                f"Which flight would you like me to book? "
                f"Just tell me the number or describe your preference "
                f"(e.g., \"the cheapest one\", \"option 2\", \"the nonstop IndiGo flight\")."
            )

            user_choice = self.ask_user_fn(question, screenshot_b64)
            print(f"  👤 User selected: {user_choice}")

            # Now use Gemini to click the selected flight
            self._click_selected_flight(user_choice, flight_list)
        else:
            print("  ℹ️  No chat callback — please select a flight manually.")
            time.sleep(10)

    def _click_selected_flight(self, user_choice: str, flight_list: str):
        """Use Gemini to click on the flight the user selected."""
        print(f"  🖱️ Clicking the selected flight...")

        screenshot = self.page.screenshot(type="png")
        config = get_generate_config()

        prompt = f"""You are on a flight search results page.

The user was shown these options:
{flight_list}

The user chose: "{user_choice}"

TASK: Click on the flight that matches the user's choice. 
If they said a number, click that numbered option.
If they described a preference, find the matching flight and click it.
Click on the flight row/card to select it."""

        parts = [Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")]
        contents = [Content(role="user", parts=parts)]

        for turn in range(8):
            print(f"  🤖 Turn {turn + 1}...")

            response = client.models.generate_content(
                model=MODEL_NAME, contents=contents, config=config,
            )

            candidate = response.candidates[0]
            contents.append(candidate.content)

            fn_calls = [
                p.function_call for p in candidate.content.parts
                if hasattr(p, "function_call") and p.function_call
            ]

            if not fn_calls:
                print("  ✓ Flight selected!")
                break

            results = execute_function_calls(candidate, self.page)
            func_responses, screenshot = get_function_responses(self.page, results)

            resp_parts = [Part(function_response=fr) for fr in func_responses]
            if screenshot:
                resp_parts.append(Part.from_bytes(data=screenshot, mime_type="image/png"))
            contents.append(Content(role="user", parts=resp_parts))
            time.sleep(1)

    def _proceed_to_booking(self):
        """
        After flight is selected, use AI to click through booking steps
        (select flight, continue, fill details) up to the payment page.
        """
        print("📋 Proceeding to booking page...")

        screenshot = self.page.screenshot(type="png")
        config = get_generate_config()

        prompt = """You are on a flight booking website. A flight has just been selected.

TASK: Proceed through the booking flow:
1. If there's a "Book" or "Select" or "Continue" button, click it
2. If asked for passenger details, look at the form but DO NOT fill payment info
3. Keep clicking "Continue" / "Next" / "Proceed" until you reach the PAYMENT page
4. STOP when you see payment fields (credit card, UPI, etc.) — do NOT fill those

Navigate through the booking flow but STOP at payment."""

        parts = [Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")]
        contents = [Content(role="user", parts=parts)]

        for turn in range(15):
            print(f"  🤖 Turn {turn + 1}...")

            response = client.models.generate_content(
                model=MODEL_NAME, contents=contents, config=config,
            )

            candidate = response.candidates[0]
            contents.append(candidate.content)

            # Print reasoning
            text_parts = [
                p.text for p in candidate.content.parts
                if hasattr(p, 'text') and p.text and not hasattr(p, 'thought')
            ]
            if text_parts:
                print(f"  💬 {' '.join(text_parts)[:150]}")

            fn_calls = [
                p.function_call for p in candidate.content.parts
                if hasattr(p, "function_call") and p.function_call
            ]

            if not fn_calls:
                print("  ✓ Reached booking/payment page")
                break

            results = execute_function_calls(candidate, self.page)
            func_responses, screenshot = get_function_responses(self.page, results)

            resp_parts = [Part(function_response=fr) for fr in func_responses]
            if screenshot:
                resp_parts.append(Part.from_bytes(data=screenshot, mime_type="image/png"))
            contents.append(Content(role="user", parts=resp_parts))
            time.sleep(1)

    def _handoff_payment(self):
        """
        Notify the user via chat to complete payment in the browser window.
        The browser stays open for them.
        """
        print("💳 Handing off to user for payment...")

        if self.ask_user_fn:
            # Take final screenshot to show current state
            screenshot_bytes = self.page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            self.ask_user_fn(
                "✅ **Flight booked!** I've selected your flight and reached the payment page.\n\n"
                "💳 **Please complete the payment** in the browser window that's open on your screen.\n\n"
                "I've stopped here for your safety — I won't enter any payment details.\n"
                "Just switch to the browser window and finish the payment. 🙌",
                screenshot_b64,
            )
        else:
            print("  ✅ Please complete payment in the browser window.")

    def _build_search_task(self) -> str:
        """Build search task description from booking details."""
        d = self.booking_details
        task = f"Origin: {d['origin']}\nDestination: {d['destination']}\n"
        task += f"Departure: {d['departure_date']}\nTrip: {d.get('trip_type', 'one-way')}\n"
        if d.get('trip_type') == 'round-trip' and d.get('return_date'):
            task += f"Return: {d['return_date']}\n"
        p = d.get('passengers', {'adults': 1, 'children': 0, 'infants': 0})
        task += f"Passengers: {p.get('adults', 1)} adult(s)"
        if p.get('children', 0): task += f", {p['children']} child(ren)"
        if p.get('infants', 0): task += f", {p['infants']} infant(s)"
        task += f"\nClass: {d.get('class', 'economy')}\n"
        return task

    def _cleanup(self):
        try:
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except Exception:
            pass


def execute_flight_booking(booking_details: Dict, ask_user_fn=None):
    """Execute flight booking workflow."""
    workflow = FlightBookingWorkflow(booking_details, ask_user_fn=ask_user_fn)
    workflow.execute()
