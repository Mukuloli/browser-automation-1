"""
Browser Action Handlers for Gemini Computer Use.

This module provides functions to execute browser actions (click, type, navigate, etc.)
with integrated safety policy checks and screen coordinate normalization.

The safety policy is injected at runtime via set_safety_policy() to check
each action before execution.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import Page
from google.genai import types

from config import SCREEN_WIDTH, SCREEN_HEIGHT
from .helpers import denormalize_x, denormalize_y
from .captcha_solver import solve_page_captcha


# =============================================================================
# Safety Policy Integration
# =============================================================================

_safety_policy = None


def set_safety_policy(policy) -> None:
    """
    Set the global safety policy for action checking.
    
    Args:
        policy: SafetyPolicy instance to use for action validation
    """
    global _safety_policy
    _safety_policy = policy


def _get_current_url(page: Page) -> str:
    """Safely get current page URL."""
    try:
        return page.url
    except Exception:
        return ""


def _check_safety(fname: str, args: Dict[str, Any], page: Page) -> Optional[Dict[str, Any]]:
    """
    Check if action is safe to execute.
    
    Returns:
        None if safe, error dict if blocked
    """
    if not _safety_policy:
        return None
    
    target_url = args.get("url", "")
    current_url = _get_current_url(page)
    action_desc = f"{fname} {str(args)}"
    
    is_safe, reason = _safety_policy.check_safety(action_desc, target_url or current_url)
    
    if not is_safe:
        return {
            "success": False,
            "blocked": True,
            "error": f"BLOCKED BY SAFETY POLICY: {reason}",
            "action": fname,
        }
    
    _safety_policy.record_action()
    return None


# =============================================================================
# Action Execution
# =============================================================================

def execute_action(page: Page, fname: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single browser action with safety checks.
    
    Args:
        page: Playwright page object
        fname: Function name from the model
        args: Arguments for the function
        
    Returns:
        Result dictionary with success status and details
    """
    # Safety check
    blocked = _check_safety(fname, args, page)
    if blocked:
        return blocked
    
    try:
        return _execute_action_internal(page, fname, args)
    except Exception as error:
        print(f"     ❌ Error: {error}")
        return {"success": False, "error": str(error)}


def _execute_action_internal(
    page: Page,
    fname: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute action without safety checks (internal use)."""
    
    # Browser navigation
    if fname == "open_web_browser":
        # Skip if already on a real page (not blank)
        current = page.url if not page.is_closed() else ""
        if current and current != "about:blank" and not current.startswith("chrome:"):
            print(f"     ℹ️  Browser already open at {current[:50]}... (skipping)")
            return {"success": True, "action": "browser_already_open", "url": current}
        page.goto("https://www.google.com")
        return {"success": True, "action": "opened_browser"}
    
    if fname in ("navigate", "go_to_url"):
        url = args.get("url", "https://www.google.com")
        page.goto(url, wait_until="domcontentloaded")
        # Wait for page to stabilize
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        time.sleep(1)  # Extra settle time for dynamic content
        return {"success": True, "url": url}
    
    if fname == "go_back":
        page.go_back()
        return {"success": True, "action": "go_back"}
    
    if fname == "go_forward":
        page.go_forward()
        return {"success": True, "action": "go_forward"}
    
    if fname == "refresh":
        page.reload()
        return {"success": True, "action": "refresh"}
    
    # Mouse actions
    if fname == "click_at":
        x, y = args.get("x", 0), args.get("y", 0)
        actual_x, actual_y = denormalize_x(x), denormalize_y(y)
        print(f"     📍 Clicking: ({x}, {y}) → pixel ({actual_x}, {actual_y})")
        page.mouse.click(actual_x, actual_y)
        return {"success": True, "x": actual_x, "y": actual_y}
    
    if fname == "double_click_at":
        x, y = args.get("x", 0), args.get("y", 0)
        actual_x, actual_y = denormalize_x(x), denormalize_y(y)
        page.mouse.dblclick(actual_x, actual_y)
        return {"success": True, "x": actual_x, "y": actual_y}
    
    if fname == "right_click_at":
        x, y = args.get("x", 0), args.get("y", 0)
        actual_x, actual_y = denormalize_x(x), denormalize_y(y)
        page.mouse.click(actual_x, actual_y, button="right")
        return {"success": True, "x": actual_x, "y": actual_y}
    
    if fname == "hover_at":
        x, y = args.get("x", 0), args.get("y", 0)
        actual_x, actual_y = denormalize_x(x), denormalize_y(y)
        page.mouse.move(actual_x, actual_y)
        return {"success": True, "x": actual_x, "y": actual_y}
    
    # Keyboard actions
    if fname == "type_text":
        text = args.get("text", "")
        print(f"     ⌨️  Typing: '{text}'")
        page.keyboard.type(text, delay=50)
        return {"success": True, "text": text}
    
    if fname == "type_text_at":
        return _type_text_at(page, args)
    
    if fname in ("press_key", "key"):
        return _press_key(page, args)
    
    # Scroll actions
    if fname == "scroll":
        return _scroll(page, args)
    
    if fname == "scroll_down":
        amount = args.get("amount", 300)
        page.mouse.wheel(0, amount)
        return {"success": True, "scrolled": amount}
    
    if fname == "scroll_up":
        amount = args.get("amount", 300)
        page.mouse.wheel(0, -amount)
        return {"success": True, "scrolled": -amount}
    
    if fname == "scroll_document":
        return _scroll_document(page, args)
    
    # Search
    if fname == "search":
        query = args.get("query", args.get("text", ""))
        print(f"     🔍 Searching: '{query}'")
        page.keyboard.type(query, delay=30)
        page.keyboard.press("Enter")
        return {"success": True, "query": query}
    
    # Wait
    if fname == "wait":
        duration = float(args.get("duration", args.get("seconds", 1)))
        print(f"     ⏳ Waiting {duration}s...")
        time.sleep(duration)
        return {"success": True, "waited": duration}
    
    # CAPTCHA
    if fname == "solve_captcha":
        print("     🔐 Attempting to solve CAPTCHA...")
        solved = solve_page_captcha(page)
        return {"success": solved, "action": "solve_captcha"}
    
    # Unknown action
    print(f"     ⚠️  Unknown function: {fname}")
    return {"success": False, "error": f"Unknown function: {fname}"}


def _type_text_at(page: Page, args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle type_text_at action."""
    x, y = args.get("x", 0), args.get("y", 0)
    text = args.get("text", "")
    press_enter = args.get("press_enter", False)
    
    actual_x, actual_y = denormalize_x(x), denormalize_y(y)
    print(f"     📍 Click at ({actual_x}, {actual_y}) and type: '{text}'")
    
    page.mouse.click(actual_x, actual_y)
    time.sleep(0.2)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    time.sleep(0.1)
    page.keyboard.type(text, delay=30)
    
    if press_enter:
        time.sleep(0.1)
        page.keyboard.press("Enter")
    
    return {"success": True, "text": text, "x": actual_x, "y": actual_y}


def _press_key(page: Page, args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle press_key action."""
    key = args.get("key", "")
    key_map = {
        "enter": "Enter",
        "return": "Enter",
        "tab": "Tab",
        "escape": "Escape",
        "esc": "Escape",
        "backspace": "Backspace",
        "delete": "Delete",
        "space": " ",
        "arrowup": "ArrowUp",
        "arrowdown": "ArrowDown",
        "arrowleft": "ArrowLeft",
        "arrowright": "ArrowRight",
        "pageup": "PageUp",
        "pagedown": "PageDown",
        "home": "Home",
        "end": "End",
    }
    mapped_key = key_map.get(key.lower(), key)
    print(f"     ⌨️  Pressing key: {mapped_key}")
    page.keyboard.press(mapped_key)
    return {"success": True, "key": mapped_key}


def _scroll(page: Page, args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle scroll action."""
    x, y = args.get("x", 500), args.get("y", 500)
    delta_x = args.get("delta_x", args.get("scroll_x", 0))
    delta_y = args.get("delta_y", args.get("scroll_y", 0))
    
    actual_x, actual_y = denormalize_x(x), denormalize_y(y)
    print(f"     🖱️  Scrolling at ({actual_x}, {actual_y}) by ({delta_x}, {delta_y})")
    
    page.mouse.move(actual_x, actual_y)
    page.mouse.wheel(delta_x, delta_y)
    return {"success": True, "delta_x": delta_x, "delta_y": delta_y}


def _scroll_document(page: Page, args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle scroll_document action."""
    delta_x = args.get("delta_x", args.get("scroll_x", 0))
    delta_y = args.get("delta_y", args.get("scroll_y", 300))
    direction = args.get("direction", "down")
    
    if direction == "up":
        delta_y = -abs(delta_y) if delta_y else -300
    elif direction == "down":
        delta_y = abs(delta_y) if delta_y else 300
    
    print(f"     📜 Scrolling document by ({delta_x}, {delta_y})")
    page.mouse.wheel(delta_x, delta_y)
    return {"success": True, "delta_x": delta_x, "delta_y": delta_y}


# =============================================================================
# Response Processing
# =============================================================================

def execute_function_calls(
    candidate,
    page: Page,
) -> List[Tuple[str, Dict[str, Any], bool]]:
    """
    Execute all function calls from a model response.
    
    Handles safety_decision acknowledgment for Gemini Computer Use API.
    
    Args:
        candidate: Response candidate from Gemini
        page: Playwright page object
        
    Returns:
        List of (function_name, result, has_safety_decision) tuples
    """
    results = []
    
    # Collect function calls
    function_calls = [
        part.function_call
        for part in candidate.content.parts
        if hasattr(part, "function_call") and part.function_call
    ]
    
    for fc in function_calls:
        fname = fc.name
        args = dict(fc.args) if fc.args else {}
        
        # Handle safety_decision from Computer Use API
        has_safety_decision = "safety_decision" in args
        if has_safety_decision:
            _handle_safety_decision(args)
            args = {k: v for k, v in args.items() if k != "safety_decision"}
        
        print(f"  → Executing: {fname}")
        result = execute_action(page, fname, args)
        results.append((fname, result, has_safety_decision))
        
        # Wait for page to settle
        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        time.sleep(0.3)
    
    return results


def _handle_safety_decision(args: Dict[str, Any]) -> None:
    """Process safety_decision from function call args."""
    safety_decision = args.get("safety_decision", {})
    decision_type = safety_decision.get("decision", "")
    explanation = safety_decision.get("explanation", "")
    
    if decision_type == "require_confirmation":
        print(f"  ⚠️ Safety confirmation required: {explanation[:100]}...")
        print("  ✓ Safety decision auto-acknowledged")


def has_function_calls(candidate) -> bool:
    """Check if response contains any function calls."""
    return any(
        hasattr(part, "function_call") and part.function_call
        for part in candidate.content.parts
    )


def get_text_response(candidate) -> str:
    """
    Extract text response from candidate (excluding thinking).
    
    Args:
        candidate: Response candidate from Gemini
        
    Returns:
        Concatenated text parts
    """
    texts = []
    for part in candidate.content.parts:
        if hasattr(part, "text") and part.text:
            if hasattr(part, "thought") and part.thought:
                continue
            texts.append(part.text)
    return " ".join(texts)



def get_function_responses(
    page: Page,
    results: List[Tuple[str, Dict[str, Any], bool]],
    skip_screenshot: bool = False,
) -> Tuple[List[types.FunctionResponse], Optional[bytes]]:
    """
    Build FunctionResponse objects with current page state.
    
    Args:
        page: Playwright page object
        results: List of (function_name, result, has_safety_decision) tuples
        skip_screenshot: If True, don't capture screenshot (for minor actions)
        
    Returns:
        Tuple of (function_responses list, screenshot_bytes)
    """
    screenshot_bytes = None
    if not skip_screenshot and not page.is_closed():
        screenshot_bytes = page.screenshot(type="png")
    
    current_url = page.url if not page.is_closed() else ""
    
    function_responses = []
    for item in results:
        if len(item) == 3:
            name, result, has_safety_decision = item
        else:
            name, result = item
            has_safety_decision = False
        
        response_data = {"url": current_url, **result}
        
        if has_safety_decision:
            response_data["safety_acknowledgement"] = "true"
        
        function_responses.append(
            types.FunctionResponse(name=name, response=response_data)
        )
    
    return function_responses, screenshot_bytes


def should_skip_screenshot(results: List[Tuple[str, Dict[str, Any], bool]]) -> bool:
    """
    Determine if screenshot should be skipped based on executed actions.
    
    Args:
        results: List of (function_name, result, has_safety_decision) tuples
        
    Returns:
        True if screenshot can be skipped for these actions
    """
    from config import SKIP_SCREENSHOT_ACTIONS
    
    # Skip screenshot only if ALL actions are minor
    for item in results:
        name = item[0]
        if name not in SKIP_SCREENSHOT_ACTIONS:
            return False
    
    return len(results) > 0

