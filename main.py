#!/usr/bin/env python3
"""
Browser Automation System - Main Entry Point.

This module orchestrates all components of the Gemini-powered browser automation
system. It integrates safety checks, user confirmation, task planning, action
execution, and visual validation.

Usage:
    python main.py "Go to YouTube and search for music"
    python main.py "Open Wikipedia and search for Python"

Components:
    - SafetyPolicy: Blocks dangerous domains and actions
    - ConfirmationManager: Handles user approval workflow
    - TaskPlanner: Generates step-by-step execution plans
    - VisualValidator: Validates step completion via screenshots
    - Actions: Executes browser actions (click, type, navigate, etc.)
"""

import sys
import time
from typing import Optional

from google.genai.types import Content, Part
from playwright.sync_api import sync_playwright

from config import (
    client,
    get_generate_config,
    MODEL_NAME,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    ENABLE_DOM_HINTS,
)
from utils import (
    # Actions
    execute_function_calls,
    has_function_calls,
    get_text_response,
    get_function_responses,
    set_safety_policy,
    should_skip_screenshot,
    # Task Planning
    generate_plan,
    # Visual Validation
    validate_step,
    save_error,
    # Confirmation
    confirm_plan,
    confirm_step,
    # Safety
    SafetyPolicy,
    SessionScope,
    is_stopped,
    reset_stop,
    # Helpers
    print_header,
    # Optimization
    optimize_screenshot,
    format_dom_hints,
    get_image_info,
)


def run(
    goal: str,
    confirm: bool = True,
    scope: Optional[SessionScope] = None,
) -> None:
    """
    Execute browser automation task with full module integration.
    
    This function orchestrates all components:
    1. Initialize SafetyPolicy
    2. Generate execution plan via TaskPlanner
    3. Get user confirmation via ConfirmationManager
    4. Launch browser and execute steps
    5. Validate each step via VisualValidator
    
    Args:
        goal: Natural language description of the task
        confirm: Whether to require user confirmation (default: True)
        scope: Optional SessionScope to limit actions/domains
    """
    print_header("🚀 Browser Automation System")
    print(f"Goal: {goal}\n")
    
    # Initialize Safety Policy
    if scope is None:
        scope = SessionScope(
            allowed_domains=[],
            max_actions=100,
            max_tokens=200000,
            timeout_minutes=30,
            require_step_confirmation=False,
        )
    
    safety_policy = SafetyPolicy(scope)
    set_safety_policy(safety_policy)
    print("🛡️  Safety Policy initialized")
    
    # Reset emergency stop
    reset_stop()
    
    # Generate Plan
    print("\n📋 Planning with TaskPlanner...")
    plan = generate_plan(goal)
    
    # User Confirmation
    if confirm:
        approval = confirm_plan(plan)
        if approval == "no":
            print("❌ Cancelled by user")
            return
        step_mode = approval == "step"
    else:
        step_mode = False
    
    # Launch Browser
    print("\n🌐 Launching browser...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False,
        args=["--start-maximized"],
    )
    context = browser.new_context(
        viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
    )
    page = context.new_page()
    page.goto("about:blank")
    
    # Get model config
    config = get_generate_config()
    completed, failed, tokens = 0, 0, 0
    
    try:
        # Execute each step
        for step in plan.steps:
            if is_stopped():
                print("\n🛑 Emergency stop triggered!")
                break
            
            if step_mode and not confirm_step(step):
                print(f"  ⏭️  Step {step.num} skipped")
                continue
            
            print(f"\n📍 Step {step.num}: {step.action.upper()} - {step.desc}")
            
            # Wait for page to settle
            time.sleep(1)
            
            # Build initial prompt with screenshot and current URL context
            current_url = page.url if not page.is_closed() else "about:blank"
            screenshot = page.screenshot(type="png") if not page.is_closed() else None
            
            # Optimize screenshot
            if screenshot:
                original_info = get_image_info(screenshot)
                screenshot = optimize_screenshot(screenshot)
                optimized_info = get_image_info(screenshot)
                print(f"  📸 Screenshot: {original_info['width']}x{original_info['height']} ({original_info['size_bytes']:,} bytes) → {optimized_info['width']}x{optimized_info['height']} ({optimized_info['size_bytes']:,} bytes)")
            
            # Extract DOM hints if enabled
            dom_hints = ""
            if ENABLE_DOM_HINTS and not page.is_closed():
                try:
                    dom_hints = format_dom_hints(page)
                    print(f"  🔍 Extracted {len(dom_hints.split('\n'))} DOM elements")
                except Exception as e:
                    print(f"  ⚠️  DOM extraction failed: {e}")
            
            # Enhanced prompt with batching encouragement and DOM hints
            prompt = f"""You are controlling a browser. The browser is ALREADY OPEN.

CURRENT PAGE: {current_url}
(Screenshot of current page is attached below)

{dom_hints if dom_hints else ""}

YOUR TASK - Execute this step efficiently:
- Action: {step.action}
- Description: {step.desc}
- Target: {step.target}
- Value: {step.value}

IMPORTANT RULES:
1. DO NOT call open_web_browser - the browser is already open
2. If you need to navigate, use the 'navigate' function with a URL
3. Work with the CURRENT page shown in the screenshot
4. BATCH MULTIPLE ACTIONS when possible (e.g., click + type + press_key in one turn)
5. Use the DOM element coordinates provided above to click precisely
6. Close any pop-ups or modals that block your target elements
7. Complete ONLY this step efficiently, then report done

Execute the step now with minimal turns."""
            
            parts = [Part(text=prompt)]
            if screenshot:
                parts.append(Part.from_bytes(data=screenshot, mime_type="image/png"))
            contents = [Content(role="user", parts=parts)]
            
            # Agent loop for step execution
            for iteration in range(5):
                if is_stopped():
                    break
                
                print(f"  🤖 Turn {iteration + 1}...")
                
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents,
                        config=config,
                    )
                except Exception as error:
                    print(f"  ❌ API Error: {error}")
                    break
                
                # Track and display token usage
                if response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count or 0
                    response_tokens = response.usage_metadata.candidates_token_count or 0
                    turn_tokens = prompt_tokens + response_tokens
                    tokens += turn_tokens
                    print(f"  📊 Tokens: {turn_tokens:,} (prompt: {prompt_tokens:,}, response: {response_tokens:,}) | Total: {tokens:,}")
                    safety_policy.record_action(
                        response.usage_metadata.candidates_token_count or 0
                    )
                
                candidate = response.candidates[0]
                contents.append(candidate.content)
                
                # Print text response
                text = get_text_response(candidate)
                if text:
                    print(f"  💬 {text[:150]}...")
                
                # Check for function calls
                if not has_function_calls(candidate):
                    print("  ✓ Step actions complete")
                    break
                
                # Execute function calls
                print("  ⚡ Executing actions...")
                results = execute_function_calls(candidate, page)
                
                # Check for blocked actions
                for name, result, _ in results:
                    if result.get("blocked"):
                        print(f"  🛑 Action blocked: {result.get('error')}")
                
                time.sleep(0.5)
                
                # Build function responses with smart screenshot logic
                if not page.is_closed():
                    skip_screenshot = should_skip_screenshot(results)
                    func_responses, screenshot = get_function_responses(page, results, skip_screenshot)
                    
                    response_parts = [
                        Part(function_response=fr) for fr in func_responses
                    ]
                    
                    if screenshot:
                        # Optimize screenshot before sending
                        screenshot = optimize_screenshot(screenshot)
                        response_parts.append(
                            Part.from_bytes(data=screenshot, mime_type="image/png")
                        )
                    elif not skip_screenshot:
                        # If we didn't skip but have no screenshot, page might be closed
                        print("  ⚠️  Page closed, skipping screenshot")
                    
                    contents.append(Content(role="user", parts=response_parts))
            
            # Validate step completion
            if not page.is_closed():
                print("  🔍 Validating with VisualValidator...")
                validation_screenshot = page.screenshot(type="png")
                # Don't optimize validation screenshot - keep full quality for accuracy
                validation = validate_step(validation_screenshot, step.expected)
                if validation.success:
                    print(f"  ✅ Validated: {validation.reason}")
                    completed += 1
                else:
                    print(f"  ❌ Failed: {validation.reason}")
                    save_error(
                        page.screenshot(type="png"),
                        step.num,
                        validation.error_type or "failed",
                        validation.reason,
                    )
                    failed += 1
        
        # Print Summary
        _print_summary(completed, failed, tokens, plan, safety_policy)
        
        print("\n⏳ Browser open. Press Ctrl+C to close...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        _cleanup(browser, playwright)


def _print_summary(
    completed: int,
    failed: int,
    tokens: int,
    plan,
    safety_policy: SafetyPolicy,
) -> None:
    """Print execution summary."""
    print(f"\n{'=' * 60}")
    print("📊 EXECUTION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  ✅ Steps Completed: {completed}/{len(plan.steps)}")
    print(f"  ❌ Steps Failed: {failed}")
    print(f"  📊 Tokens Used: {tokens:,}")
    
    safety_summary = safety_policy.get_summary()
    print("\n🛡️  SAFETY SUMMARY")
    print(f"  Actions executed: {safety_summary['actions_executed']}")
    print(f"  Violations blocked: {safety_summary['violations_blocked']}")
    print(f"  Session duration: {safety_summary['session_duration_minutes']:.1f} min")


def _cleanup(browser, playwright) -> None:
    """Clean up browser resources."""
    try:
        browser.close()
        playwright.stop()
    except Exception:
        pass


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) > 1:
        # Check for flight booking mode
        if sys.argv[1] in ["--flight-booking", "--book-flight", "-f"]:
            from utils.flight_booking_input import (
                collect_flight_details,
                format_booking_summary,
                confirm_booking,
            )
            from utils.flight_booking_workflow import execute_flight_booking
            
            try:
                # Collect flight details
                booking_details = collect_flight_details()
                
                # Show summary
                summary = format_booking_summary(booking_details)
                print(summary)
                
                # Confirm
                if not confirm_booking():
                    print("\n❌ Booking cancelled by user.\n")
                    return
                
                # Execute booking
                print("\n🚀 Starting flight booking automation...\n")
                execute_flight_booking(booking_details)
                
            except KeyboardInterrupt:
                print("\n🛑 Interrupted by user")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            # Regular browser automation mode
            goal = " ".join(sys.argv[1:])
            run(goal)
    else:
        _print_usage()


def _print_usage() -> None:
    """Print usage information."""
    print("=" * 60)
    print("🤖 Browser Automation System")
    print("=" * 60)
    print("\nUsage:")
    print('  python main.py "your task here"')
    print("  python main.py --flight-booking")
    print("  python book_flight.py")
    print("\nExamples:")
    print('  python main.py "Go to YouTube and search for music"')
    print('  python main.py "Go to Google and search for weather"')
    print('  python main.py "Open Wikipedia and search for Python"')
    print("\nFlight Booking:")
    print("  python main.py --flight-booking")
    print("  python book_flight.py")
    print("\nIntegrated Modules:")
    print("  • SafetyPolicy      - Blocks dangerous actions")
    print("  • ConfirmationManager - User approval workflow")
    print("  • TaskPlanner       - Step-by-step plan generation")
    print("  • VisualValidator   - Screenshot-based validation")
    print("  • Actions           - Browser action execution")
    print("  • CaptchaSolver     - CAPTCHA challenge handling")
    print("  • FlightBooking     - Interactive flight booking automation")


if __name__ == "__main__":
    main()
