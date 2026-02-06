"""
Image Optimization Utilities for Browser Automation.

This module provides functions to optimize screenshots for faster processing
by the Gemini model, including downscaling, compression, and grayscale conversion.
"""

from io import BytesIO
from typing import Optional

from PIL import Image

from config import SCREENSHOT_SCALE, SCREENSHOT_QUALITY, ENABLE_GRAYSCALE


def downscale_screenshot(
    image_bytes: bytes,
    scale: Optional[float] = None,
) -> bytes:
    """
    Downscale screenshot to reduce token count.
    
    Args:
        image_bytes: Original screenshot bytes
        scale: Scale factor (0.0-1.0). If None, uses SCREENSHOT_SCALE from config
        
    Returns:
        Downscaled image bytes
    """
    if scale is None:
        scale = SCREENSHOT_SCALE
    
    if scale >= 1.0:
        return image_bytes
    
    img = Image.open(BytesIO(image_bytes))
    new_width = int(img.width * scale)
    new_height = int(img.height * scale)
    
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    output = BytesIO()
    img_resized.save(output, format="PNG")
    return output.getvalue()


def compress_image(
    image_bytes: bytes,
    quality: Optional[int] = None,
    format: str = "JPEG",
) -> bytes:
    """
    Compress image to reduce file size.
    
    Args:
        image_bytes: Original image bytes
        quality: Compression quality (0-100). If None, uses SCREENSHOT_QUALITY from config
        format: Output format ("JPEG" or "PNG")
        
    Returns:
        Compressed image bytes
    """
    if quality is None:
        quality = SCREENSHOT_QUALITY
    
    img = Image.open(BytesIO(image_bytes))
    
    # Convert RGBA to RGB for JPEG
    if format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = rgb_img
    
    output = BytesIO()
    img.save(output, format=format, quality=quality, optimize=True)
    return output.getvalue()


def convert_to_grayscale(image_bytes: bytes) -> bytes:
    """
    Convert image to grayscale to reduce data size.
    
    Args:
        image_bytes: Original image bytes
        
    Returns:
        Grayscale image bytes
    """
    img = Image.open(BytesIO(image_bytes))
    img_gray = img.convert("L")
    
    output = BytesIO()
    img_gray.save(output, format="PNG")
    return output.getvalue()


def optimize_screenshot(
    image_bytes: bytes,
    scale: Optional[float] = None,
    quality: Optional[int] = None,
    grayscale: Optional[bool] = None,
) -> bytes:
    """
    Apply all optimizations to a screenshot.
    
    This is the main function to use for optimizing screenshots before
    sending them to the Gemini model.
    
    Args:
        image_bytes: Original screenshot bytes
        scale: Scale factor (0.0-1.0). If None, uses SCREENSHOT_SCALE from config
        quality: Compression quality (0-100). If None, uses SCREENSHOT_QUALITY from config
        grayscale: Whether to convert to grayscale. If None, uses ENABLE_GRAYSCALE from config
        
    Returns:
        Optimized image bytes
    """
    if grayscale is None:
        grayscale = ENABLE_GRAYSCALE
    
    # Step 1: Downscale
    optimized = downscale_screenshot(image_bytes, scale)
    
    # Step 2: Convert to grayscale if enabled
    if grayscale:
        optimized = convert_to_grayscale(optimized)
    
    # Step 3: Compress
    # Use JPEG for grayscale, PNG for color to preserve quality
    format = "JPEG" if grayscale else "PNG"
    optimized = compress_image(optimized, quality, format)
    
    return optimized


def get_image_info(image_bytes: bytes) -> dict:
    """
    Get information about an image.
    
    Args:
        image_bytes: Image bytes
        
    Returns:
        Dictionary with width, height, format, mode, and size
    """
    img = Image.open(BytesIO(image_bytes))
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
        "size_bytes": len(image_bytes),
    }
