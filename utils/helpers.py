"""
Helper utilities for browser automation.

This module provides utility functions for coordinate conversion and
console output formatting.
"""

from typing import Optional

from config import SCREEN_WIDTH, SCREEN_HEIGHT


def denormalize_x(x: int, screen_width: Optional[int] = None) -> int:
    """
    Convert normalized x coordinate (0-1000) to actual pixel coordinate.
    
    The Gemini model returns coordinates in a normalized 0-1000 range.
    This function converts them to actual screen pixels.
    
    Args:
        x: Normalized x coordinate (0-1000)
        screen_width: Screen width in pixels (defaults to SCREEN_WIDTH)
        
    Returns:
        Actual pixel x coordinate
    """
    width = screen_width or SCREEN_WIDTH
    return int(x / 1000 * width)


def denormalize_y(y: int, screen_height: Optional[int] = None) -> int:
    """
    Convert normalized y coordinate (0-1000) to actual pixel coordinate.
    
    The Gemini model returns coordinates in a normalized 0-1000 range.
    This function converts them to actual screen pixels.
    
    Args:
        y: Normalized y coordinate (0-1000)
        screen_height: Screen height in pixels (defaults to SCREEN_HEIGHT)
        
    Returns:
        Actual pixel y coordinate
    """
    height = screen_height or SCREEN_HEIGHT
    return int(y / 1000 * height)


def print_header(text: str, char: str = "=", width: int = 60) -> None:
    """
    Print a formatted header with decorative borders.
    
    Args:
        text: Header text to display
        char: Character to use for border (default: "=")
        width: Width of the border line (default: 60)
    """
    print(char * width)
    print(text)
    print(char * width)


def print_step(step_num: int) -> None:
    """
    Print a step indicator with decorative borders.
    
    Args:
        step_num: Step number to display
    """
    print(f"\n{'=' * 50}")
    print(f"📍 Step {step_num}")
    print(f"{'=' * 50}")
