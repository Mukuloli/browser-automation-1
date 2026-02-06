"""
Utils Package - Browser Automation Helper Modules.

This package provides all utility modules for the Gemini-powered browser
automation system. All modules are initialized lazily for efficiency.

Modules:
    actions: Browser action execution (click, type, navigate, etc.)
    task_planner: Natural language to execution plan conversion
    visual_validator: Screenshot-based step validation
    confirmation: User approval workflow
    safety_policy: Security and safety enforcement
    captcha_solver: CAPTCHA detection and handling
    helpers: Utility functions for coordinates and display
"""

from typing import TYPE_CHECKING

# Core module imports
from .actions import (
    execute_function_calls,
    has_function_calls,
    get_text_response,
    get_function_responses,
    set_safety_policy,
    execute_action,
    should_skip_screenshot,
)
from .task_planner import TaskPlanner, TaskPlan, Step
from .visual_validator import VisualValidator, ValidationResult
from .captcha_solver import detect_captcha_type, solve_page_captcha, CaptchaSolver
from .safety_policy import (
    SafetyPolicy,
    SessionScope,
    is_emergency_stopped,
    trigger_emergency_stop,
    reset_emergency_stop,
)
from .confirmation import ConfirmationManager
from .helpers import print_header, print_step, denormalize_x, denormalize_y
from .image_optimizer import optimize_screenshot, get_image_info
from .dom_extractor import format_dom_hints, extract_interactive_elements


# =============================================================================
# Singleton Instances (Lazy Initialization)
# =============================================================================

_planner: TaskPlanner = None
_validator: VisualValidator = None
_confirmation_manager: ConfirmationManager = None


def _get_planner() -> TaskPlanner:
    """Get or create TaskPlanner singleton."""
    global _planner
    if _planner is None:
        _planner = TaskPlanner()
    return _planner


def _get_validator() -> VisualValidator:
    """Get or create VisualValidator singleton."""
    global _validator
    if _validator is None:
        _validator = VisualValidator()
    return _validator


def _get_confirmation_manager() -> ConfirmationManager:
    """Get or create ConfirmationManager singleton."""
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager


# =============================================================================
# Convenience Functions
# =============================================================================

# Alias for backward compatibility
Plan = TaskPlan


def generate_plan(goal: str) -> TaskPlan:
    """
    Generate an execution plan from a natural language goal.
    
    Args:
        goal: Natural language task description
        
    Returns:
        TaskPlan with steps to execute
    """
    planner = _get_planner()
    plan = planner.plan(goal)
    planner.print_plan(plan)
    return plan


def validate_step(screenshot: bytes, expected_state: str) -> ValidationResult:
    """
    Validate if a step succeeded by analyzing the screenshot.
    
    Args:
        screenshot: PNG screenshot bytes
        expected_state: Description of expected result
        
    Returns:
        ValidationResult with success status and reason
    """
    return _get_validator().validate(screenshot, expected_state)


def save_error(
    screenshot: bytes,
    step_num: int,
    error_type: str,
    reason: str,
) -> str:
    """
    Save an error screenshot with metadata.
    
    Args:
        screenshot: PNG screenshot bytes
        step_num: Step number that failed
        error_type: Type of error
        reason: Error description
        
    Returns:
        Path to saved screenshot
    """
    return _get_validator().save_error_screenshot(
        screenshot, step_num, error_type, reason
    )


def confirm_plan(plan: TaskPlan) -> str:
    """
    Show plan preview and request user approval.
    
    Args:
        plan: TaskPlan to display
        
    Returns:
        'yes' for full approval, 'step' for step-by-step, 'no' for cancel
    """
    cm = _get_confirmation_manager()
    cm.show_plan_preview(plan)
    cm.show_emergency_stop_instructions()
    return cm.request_approval()


def confirm_step(step: Step) -> bool:
    """
    Request approval for a specific step.
    
    Args:
        step: Step to confirm
        
    Returns:
        True if approved, False otherwise
    """
    return _get_confirmation_manager().request_step_approval(step)


# Aliases for emergency stop functions
is_stopped = is_emergency_stopped
reset_stop = reset_emergency_stop


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Actions
    "execute_function_calls",
    "has_function_calls",
    "get_text_response",
    "get_function_responses",
    "set_safety_policy",
    "execute_action",
    "should_skip_screenshot",
    # Task Planner
    "TaskPlanner",
    "TaskPlan",
    "Step",
    "Plan",
    "generate_plan",
    # Visual Validator
    "VisualValidator",
    "ValidationResult",
    "validate_step",
    "save_error",
    # CAPTCHA
    "detect_captcha_type",
    "solve_page_captcha",
    "CaptchaSolver",
    # Safety
    "SafetyPolicy",
    "SessionScope",
    "is_emergency_stopped",
    "trigger_emergency_stop",
    "reset_emergency_stop",
    "is_stopped",
    "reset_stop",
    # Confirmation
    "ConfirmationManager",
    "confirm_plan",
    "confirm_step",
    # Helpers
    "print_header",
    "print_step",
    "denormalize_x",
    "denormalize_y",
    # Optimization
    "optimize_screenshot",
    "get_image_info",
    "format_dom_hints",
    "extract_interactive_elements",
]
