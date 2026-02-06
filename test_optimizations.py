"""
Quick test script to verify performance optimizations are working.

This script tests the image optimizer and DOM extractor modules.
"""

from utils.image_optimizer import optimize_screenshot, get_image_info
from utils.dom_extractor import format_dom_hints
from playwright.sync_api import sync_playwright
import time

def test_image_optimization():
    """Test image optimization functionality."""
    print("=" * 60)
    print("Testing Image Optimization")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("https://www.google.com")
        
        # Capture original screenshot
        original = page.screenshot(type="png")
        original_info = get_image_info(original)
        
        print(f"\n📸 Original Screenshot:")
        print(f"   Size: {original_info['width']}x{original_info['height']}")
        print(f"   Bytes: {original_info['size_bytes']:,}")
        print(f"   Format: {original_info['format']}")
        
        # Optimize screenshot
        start = time.time()
        optimized = optimize_screenshot(original)
        duration = time.time() - start
        
        optimized_info = get_image_info(optimized)
        
        print(f"\n✨ Optimized Screenshot:")
        print(f"   Size: {optimized_info['width']}x{optimized_info['height']}")
        print(f"   Bytes: {optimized_info['size_bytes']:,}")
        print(f"   Format: {optimized_info['format']}")
        print(f"   Time: {duration*1000:.2f}ms")
        
        # Calculate reduction
        size_reduction = (1 - optimized_info['size_bytes'] / original_info['size_bytes']) * 100
        print(f"\n📊 Size Reduction: {size_reduction:.1f}%")
        
        browser.close()

def test_dom_extraction():
    """Test DOM metadata extraction."""
    print("\n" + "=" * 60)
    print("Testing DOM Metadata Extraction")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("https://www.google.com")
        page.wait_for_load_state("networkidle")
        
        # Extract DOM hints
        start = time.time()
        dom_hints = format_dom_hints(page)
        duration = time.time() - start
        
        print(f"\n🔍 DOM Hints Extracted:")
        print(f"   Elements: {len(dom_hints.split(chr(10)))}")
        print(f"   Time: {duration*1000:.2f}ms")
        print(f"\n📝 Sample Output:")
        print(dom_hints[:500] + "..." if len(dom_hints) > 500 else dom_hints)
        
        browser.close()

if __name__ == "__main__":
    print("\n🚀 Performance Optimization Test Suite\n")
    
    try:
        test_image_optimization()
        test_dom_extraction()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
