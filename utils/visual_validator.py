"""
Visual Validator Module for Browser Automation.

This module uses Gemini Vision to validate browser state by analyzing screenshots.
It detects success/failure states, CAPTCHAs, error pages, and captures error
screenshots with metadata for debugging.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from google.genai.types import Content, Part
from playwright.sync_api import Page

from config import client


# =============================================================================
# Constants
# =============================================================================

ERROR_SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "error_screenshots",
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ValidationResult:
    """
    Result of visual validation.
    
    Attributes:
        success: Whether the expected state was achieved
        reason: Human-readable explanation
        confidence: Confidence score (0.0 to 1.0)
        error_type: Type of error if detected
        screenshot_path: Path to saved error screenshot
    """
    
    success: bool
    reason: str
    confidence: float
    error_type: Optional[str] = None
    screenshot_path: Optional[str] = None


# =============================================================================
# Prompts
# =============================================================================

VALIDATOR_PROMPT = """Analyze this browser screenshot and determine if the expected state was achieved.

EXPECTED STATE: {expected}

Analyze the screenshot and respond with ONLY this JSON format:
{{
    "success": true/false,
    "reason": "Brief explanation of what you see",
    "confidence": 0.0-1.0,
    "error_type": null or "captcha" or "error_page" or "not_found" or "blocked" or "unexpected"
}}

DETECTION RULES:
1. success=true ONLY if the expected state is clearly visible
2. Detect ERROR pages (404, 500, "Page not found", connection errors)
3. Detect CAPTCHA challenges (reCAPTCHA, "verify you're human", image puzzles)
4. Detect BLOCKED states ("unusual traffic", "access denied", rate limiting)
5. Set error_type appropriately if any issues detected
6. Be strict - if unsure, set success=false with lower confidence

Return ONLY valid JSON, no explanation."""

QUICK_CHECK_PROMPT = """Analyze this browser screenshot for any ERROR states.

Check for:
1. Error pages (404, 500, "Page not found")
2. CAPTCHA challenges
3. Access blocked messages
4. Connection errors
5. Any other failure indicators

Respond with ONLY this JSON:
{{
    "has_error": true/false,
    "error_type": null or "captcha" or "error_page" or "not_found" or "blocked" or "connection_error",
    "description": "What you see"
}}"""


# =============================================================================
# Visual Validator
# =============================================================================

class VisualValidator:
    """
    Validates browser state using Gemini Vision.
    
    Analyzes screenshots to determine if expected states are achieved
    and detects common error conditions.
    """
    
    MODEL = "gemini-2.5-flash"
    
    def __init__(self) -> None:
        """Initialize validator and ensure screenshot directory exists."""
        self._ensure_screenshot_dir()
    
    def _ensure_screenshot_dir(self) -> None:
        """Create error screenshot directory if needed."""
        os.makedirs(ERROR_SCREENSHOT_DIR, exist_ok=True)
    
    def validate(self, screenshot: bytes, expected_state: str) -> ValidationResult:
        """
        Validate if expected state is visible in screenshot.
        
        Args:
            screenshot: PNG screenshot bytes
            expected_state: Description of expected visual state
            
        Returns:
            ValidationResult with success/failure and details
        """
        prompt = VALIDATOR_PROMPT.format(expected=expected_state)
        
        response = client.models.generate_content(
            model=self.MODEL,
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part(text=prompt),
                        Part.from_bytes(data=screenshot, mime_type="image/png"),
                    ],
                )
            ],
        )
        
        return self._parse_validation_response(response.text)
    
    def _parse_validation_response(self, text: str) -> ValidationResult:
        """Parse validation response JSON."""
        try:
            text = self._clean_json_response(text)
            result = json.loads(text)
            
            return ValidationResult(
                success=result.get("success", False),
                reason=result.get("reason", "Unknown"),
                confidence=result.get("confidence", 0.5),
                error_type=result.get("error_type"),
            )
        except json.JSONDecodeError as error:
            print(f"⚠️ Failed to parse validation JSON: {error}")
            return ValidationResult(
                success=False,
                reason=f"Validation parsing error: {text[:100]}",
                confidence=0.0,
                error_type="unexpected",
            )
    
    def _clean_json_response(self, text: str) -> str:
        """Remove markdown code blocks from response."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()
    
    def save_error_screenshot(
        self,
        screenshot: bytes,
        step_num: int,
        error_type: str,
        reason: str,
    ) -> str:
        """
        Save error screenshot with metadata.
        
        Args:
            screenshot: PNG screenshot bytes
            step_num: Step number that failed
            error_type: Type of error
            reason: Error description
            
        Returns:
            Path to saved screenshot
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"error_{timestamp}_step{step_num}"
        
        # Save screenshot
        screenshot_path = os.path.join(ERROR_SCREENSHOT_DIR, f"{filename}.png")
        with open(screenshot_path, "wb") as f:
            f.write(screenshot)
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "step_num": step_num,
            "error_type": error_type,
            "reason": reason,
        }
        metadata_path = os.path.join(ERROR_SCREENSHOT_DIR, f"{filename}.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📸 Error screenshot saved: {screenshot_path}")
        return screenshot_path
    
    def quick_check(self, page: Page) -> ValidationResult:
        """
        Quick check for common error states.
        
        Args:
            page: Playwright page object
            
        Returns:
            ValidationResult indicating if errors are present
        """
        try:
            screenshot = page.screenshot(type="png")
            
            response = client.models.generate_content(
                model=self.MODEL,
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part(text=QUICK_CHECK_PROMPT),
                            Part.from_bytes(data=screenshot, mime_type="image/png"),
                        ],
                    )
                ],
            )
            
            text = self._clean_json_response(response.text)
            result = json.loads(text)
            
            if result.get("has_error"):
                return ValidationResult(
                    success=False,
                    reason=result.get("description", "Error detected"),
                    confidence=0.8,
                    error_type=result.get("error_type"),
                )
            
            return ValidationResult(
                success=True,
                reason="No errors detected",
                confidence=0.9,
                error_type=None,
            )
            
        except Exception as error:
            return ValidationResult(
                success=False,
                reason=f"Quick check failed: {error}",
                confidence=0.0,
                error_type="unexpected",
            )
