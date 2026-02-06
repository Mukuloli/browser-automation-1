"""
Flight Booking Workflow Automation.

This module handles the automated flight booking workflow including
search execution, flight selection, and navigation to payment.
"""

from typing import Dict, Optional
from playwright.sync_api import Page, sync_playwright

from config import SCREEN_WIDTH, SCREEN_HEIGHT
from utils.actions import execute_action
from utils.helpers import print_header


class FlightBookingWorkflow:
    """Automated flight booking workflow."""
    
    def __init__(self, booking_details: Dict):
        """
        Initialize flight booking workflow.
        
        Args:
            booking_details: Dictionary with all booking details from user input
        """
        self.booking_details = booking_details
        self.page: Optional[Page] = None
        self.browser = None
        self.playwright = None
    
    def execute(self):
        """Execute the complete flight booking workflow."""
        print_header("🚀 Starting Flight Booking Automation")
        
        try:
            # Launch browser
            self._launch_browser()
            
            # Execute workflow steps
            self._navigate_to_booking_site()
            self._fill_search_form()
            self._execute_search()
            self._select_flight()
            self._navigate_to_payment()
            
            print("\n✅ Automation complete! Browser will remain open for manual payment.")
            print("🛑 Press Ctrl+C to close the browser when done.\n")
            
            # Keep browser open
            import time
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self._cleanup()
    
    def _launch_browser(self):
        """Launch browser with appropriate settings."""
        print("🌐 Launching browser...")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = self.browser.new_context(
            viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
        )
        self.page = context.new_page()
    
    def _navigate_to_booking_site(self):
        """Navigate to the flight booking website."""
        print("📍 Navigating to booking website...")
        
        # Using Google Flights as default
        # Can be changed to MakeMyTrip, Goibibo, etc.
        self.page.goto("https://www.google.com/travel/flights")
        self.page.wait_for_load_state("networkidle")
        
        import time
        time.sleep(2)  # Allow page to fully load
    
    def _fill_search_form(self):
        """Fill the flight search form with user details."""
        print("📝 Filling search form...")
        
        details = self.booking_details
        
        # This is a template - actual implementation depends on the website
        # For Google Flights, we'll use natural language automation
        
        from config import client, get_generate_config, MODEL_NAME
        from google.genai.types import Content, Part
        
        # Build search task
        task = self._build_search_task()
        
        # Use Gemini to fill the form
        screenshot = self.page.screenshot(type="png")
        
        config = get_generate_config()
        
        prompt = f"""You are controlling a browser on a flight booking website.

CURRENT PAGE: {self.page.url}

YOUR TASK: Fill the flight search form with these details:
{task}

IMPORTANT:
1. Click on the origin field and type the city name
2. Click on the destination field and type the city name
3. Click on the date picker and select the departure date
4. If round-trip, also select return date
5. Set passenger count if needed
6. Set travel class if needed
7. DO NOT click the search button yet - just fill the form

Execute these steps now."""
        
        parts = [Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")]
        contents = [Content(role="user", parts=parts)]
        
        # Execute form filling
        for iteration in range(10):
            print(f"  🤖 Turn {iteration + 1}...")
            
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
            
            candidate = response.candidates[0]
            contents.append(candidate.content)
            
            # Check for function calls
            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if hasattr(part, "function_call") and part.function_call
            ]
            
            if not function_calls:
                print("  ✓ Form filled successfully")
                break
            
            # Execute actions
            from utils.actions import execute_function_calls, get_function_responses
            results = execute_function_calls(candidate, self.page)
            
            # Get new screenshot
            func_responses, screenshot = get_function_responses(self.page, results)
            
            from google.genai import types
            response_parts = [Part(function_response=fr) for fr in func_responses]
            if screenshot:
                response_parts.append(Part.from_bytes(data=screenshot, mime_type="image/png"))
            contents.append(Content(role="user", parts=response_parts))
            
            import time
            time.sleep(0.5)
    
    def _execute_search(self):
        """Click the search button to execute the flight search."""
        print("🔍 Executing flight search...")
        
        from config import client, get_generate_config, MODEL_NAME
        from google.genai.types import Content, Part
        
        screenshot = self.page.screenshot(type="png")
        config = get_generate_config()
        
        prompt = """Find and click the "Search" or "Search flights" button to execute the search.
After clicking, wait for the results to load."""
        
        parts = [Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")]
        contents = [Content(role="user", parts=parts)]
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )
        
        from utils.actions import execute_function_calls
        execute_function_calls(response.candidates[0], self.page)
        
        import time
        time.sleep(3)  # Wait for results
    
    def _select_flight(self):
        """Select a flight based on user preferences."""
        print("✈️  Selecting flight based on your preferences...")
        
        # This would involve analyzing flight results and selecting
        # based on time preference and price
        # For now, we'll just notify that this step needs manual selection
        print("  ℹ️  Please manually select your preferred flight")
        print("  ℹ️  The automation will continue after you click on a flight")
        
        import time
        time.sleep(5)  # Give user time to select
    
    def _navigate_to_payment(self):
        """Navigate to payment page (but don't fill payment details)."""
        print("💳 Navigating to payment page...")
        print("  ⚠️  STOPPING BEFORE PAYMENT for safety")
        print("  ℹ️  Please complete payment manually")
    
    def _build_search_task(self) -> str:
        """Build search task description from booking details."""
        details = self.booking_details
        
        task = f"""
Origin: {details['origin']}
Destination: {details['destination']}
Departure Date: {details['departure_date']}
Trip Type: {details['trip_type']}
"""
        
        if details['trip_type'] == 'round-trip':
            task += f"Return Date: {details['return_date']}\n"
        
        passengers = details['passengers']
        task += f"Passengers: {passengers['adults']} adult(s)"
        if passengers['children'] > 0:
            task += f", {passengers['children']} child(ren)"
        if passengers['infants'] > 0:
            task += f", {passengers['infants']} infant(s)"
        task += f"\nClass: {details['class']}\n"
        
        return task
    
    def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass


def execute_flight_booking(booking_details: Dict):
    """
    Execute flight booking workflow.
    
    Args:
        booking_details: Dictionary with all booking details
    """
    workflow = FlightBookingWorkflow(booking_details)
    workflow.execute()
