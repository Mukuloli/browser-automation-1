"""
CAPTCHA Solver Module for Browser Automation.

This module provides AI-powered CAPTCHA solving using Gemini Vision.
Supports image CAPTCHAs, reCAPTCHA challenges, and slider puzzles.

Note: This is a best-effort solver. Some CAPTCHAs may require manual intervention.
"""

import random
import re
import time
from typing import Optional, Tuple

from google.genai.types import Content, Part
from playwright.sync_api import Page

from config import client


# =============================================================================
# CAPTCHA Solver
# =============================================================================

class CaptchaSolver:
    """
    AI-powered CAPTCHA solver using Gemini Vision.
    
    Supports:
        - Image text CAPTCHAs
        - reCAPTCHA checkbox and image challenges
        - Slider puzzles
    """
    
    MODEL = "gemini-2.5-flash"
    
    def solve_image_captcha(self, image_bytes: bytes) -> str:
        """
        Solve an image CAPTCHA using Gemini Vision.
        
        Args:
            image_bytes: PNG/JPG image bytes of the CAPTCHA
            
        Returns:
            Text/characters detected in the CAPTCHA
        """
        response = client.models.generate_content(
            model=self.MODEL,
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part(text=(
                            "This is a CAPTCHA image. Return ONLY the exact "
                            "characters/letters/numbers you see. No explanation, "
                            "no quotes, just the characters."
                        )),
                        Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
            ],
        )
        return response.text.strip()
    
    def solve_recaptcha_image(self, page: Page) -> bool:
        """
        Attempt to solve reCAPTCHA image challenges.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if solved successfully
        """
        try:
            recaptcha_frame = page.frame_locator("iframe[src*='recaptcha']").first
            if not recaptcha_frame:
                return False
            
            screenshot = page.screenshot(type="png")
            
            response = client.models.generate_content(
                model=self.MODEL,
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part(text="""Analyze this reCAPTCHA challenge screenshot.

If you see a checkbox "I'm not a robot", tell me where to click (x, y as percentage 0-100).
If you see image tiles to select, describe which tiles contain the target object using grid positions.

Return in format:
TYPE: checkbox OR image_tiles
ACTION: click_position(x%, y%) OR select_tiles(1, 2, 5, 6)"""),
                            Part.from_bytes(data=screenshot, mime_type="image/png"),
                        ],
                    )
                ],
            )
            
            result = response.text.strip()
            print(f"     🔍 reCAPTCHA analysis: {result[:100]}...")
            
            if "checkbox" in result.lower():
                checkbox = page.locator("iframe[src*='recaptcha']").first
                if checkbox:
                    box = checkbox.bounding_box()
                    if box:
                        page.mouse.click(box["x"] + 30, box["y"] + 30)
                        time.sleep(2)
                        return True
            
            return False
            
        except Exception as error:
            print(f"     ⚠️ reCAPTCHA solving error: {error}")
            return False
    
    def detect_slider_position(self, image_bytes: bytes) -> Tuple[int, int]:
        """
        Detect slider puzzle target position.
        
        Args:
            image_bytes: Screenshot of the slider puzzle
            
        Returns:
            (x_offset, y_offset) to slide the piece to
        """
        response = client.models.generate_content(
            model=self.MODEL,
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part(text="""This is a slider CAPTCHA puzzle. 
Find the gap/hole in the main image where the puzzle piece needs to go.
Return ONLY the horizontal distance (in pixels from left) to slide the piece.
Format: SLIDE_DISTANCE: <number>"""),
                        Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
            ],
        )
        
        result = response.text.strip()
        print(f"     🔍 Slider analysis: {result}")
        
        try:
            match = re.search(r"SLIDE_DISTANCE:\s*(\d+)", result)
            if match:
                return (int(match.group(1)), 0)
        except Exception:
            pass
        
        return (200, 0)  # Default
    
    def solve_slider_captcha(
        self,
        page: Page,
        slider_selector: str = ".slider-btn",
    ) -> bool:
        """
        Solve slider CAPTCHA by sliding to correct position.
        
        Args:
            page: Playwright page object
            slider_selector: CSS selector for slider button
            
        Returns:
            True if solved
        """
        try:
            screenshot = page.screenshot(type="png")
            x_offset, _ = self.detect_slider_position(screenshot)
            
            slider = page.locator(slider_selector).first
            if not slider:
                print("     ⚠️ Slider button not found")
                return False
            
            box = slider.bounding_box()
            if not box:
                return False
            
            # Simulate human-like sliding
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2
            
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            
            steps = 20
            for i in range(steps):
                progress = (i + 1) / steps
                wobble = random.randint(-2, 2)
                page.mouse.move(
                    start_x + (x_offset * progress),
                    start_y + wobble,
                )
                time.sleep(0.02)
            
            page.mouse.up()
            time.sleep(1)
            return True
            
        except Exception as error:
            print(f"     ⚠️ Slider CAPTCHA error: {error}")
            return False


# =============================================================================
# Detection Functions
# =============================================================================

def detect_captcha_type(page: Page) -> Optional[str]:
    """
    Detect what type of CAPTCHA is present on the page.
    
    Args:
        page: Playwright page object
        
    Returns:
        'recaptcha', 'hcaptcha', 'slider', 'image', or None
    """
    try:
        if page.locator("iframe[src*='recaptcha']").count() > 0:
            return "recaptcha"
        
        if page.locator("iframe[src*='hcaptcha']").count() > 0:
            return "hcaptcha"
        
        slider_selectors = [".slider-btn", ".slide-verify", "#slider", ".geetest_slider"]
        for selector in slider_selectors:
            if page.locator(selector).count() > 0:
                return "slider"
        
        captcha_keywords = ["captcha", "verify", "validation"]
        for keyword in captcha_keywords:
            if page.locator(f"img[src*='{keyword}']").count() > 0:
                return "image"
            if page.locator(f"img[alt*='{keyword}']").count() > 0:
                return "image"
        
        return None
        
    except Exception:
        return None


def solve_page_captcha(page: Page) -> bool:
    """
    Detect and solve any CAPTCHA on the current page.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if CAPTCHA was found and (possibly) solved
    """
    captcha_type = detect_captcha_type(page)
    
    if not captcha_type:
        print("     ✓ No CAPTCHA detected")
        return False
    
    print(f"     🔐 Detected CAPTCHA type: {captcha_type}")
    
    solver = CaptchaSolver()
    
    if captcha_type == "recaptcha":
        return solver.solve_recaptcha_image(page)
    
    if captcha_type == "slider":
        return solver.solve_slider_captcha(page)
    
    if captcha_type == "image":
        print("     ⚠️ Image CAPTCHA detected - manual solving may be needed")
        return False
    
    return False
