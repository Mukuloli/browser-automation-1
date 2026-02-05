"""
Configuration for Browser Automation System.

This module contains all configuration settings, constants, and API client
initialization for the Gemini-powered browser automation system.

Environment Variables:
    GEMINI_API_KEY: Required. Your Google Gemini API key.
    SCREEN_WIDTH: Optional. Browser viewport width (default: 1440).
    SCREEN_HEIGHT: Optional. Browser viewport height (default: 900).
"""

import os
from typing import List

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# API Configuration
# =============================================================================

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

client = genai.Client(api_key=API_KEY)


# =============================================================================
# Model Configuration
# =============================================================================

MODEL_NAME: str = "gemini-2.5-computer-use-preview-10-2025"
MAX_ITERATIONS: int = 50


# =============================================================================
# Browser Configuration
# =============================================================================

SCREEN_WIDTH: int = int(os.getenv("SCREEN_WIDTH", "1440"))
SCREEN_HEIGHT: int = int(os.getenv("SCREEN_HEIGHT", "900"))


# =============================================================================
# Safety Configuration
# =============================================================================

BLOCKED_DOMAINS: List[str] = [
    "paypal.com",
    "stripe.com", 
    "*bank*",
    "*payment*",
]

BLOCKED_KEYWORDS: List[str] = [
    "pay now",
    "checkout",
    "delete account",
    "credit card",
    "cvv",
]

# Functions to exclude from Computer Use
EXCLUDED_FUNCTIONS: List[str] = [
    "drag_and_drop",
]


# =============================================================================
# Model Configuration Factory
# =============================================================================

def get_generate_config() -> types.GenerateContentConfig:
    """
    Create and return the GenerateContentConfig for Gemini API.
    
    Returns:
        GenerateContentConfig with Computer Use tool and ThinkingConfig enabled.
    """
    return types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                    excluded_predefined_functions=EXCLUDED_FUNCTIONS,
                )
            )
        ],
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )
