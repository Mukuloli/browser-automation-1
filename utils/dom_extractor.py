"""
DOM Metadata Extraction for Browser Automation.

This module extracts accessibility tree and interactive element information
from web pages to provide the model with text-based UI hints, reducing the
need for pixel-level screenshot analysis.
"""

from typing import Dict, List, Optional, Tuple

from playwright.sync_api import Page

from config import SCREEN_WIDTH, SCREEN_HEIGHT


def normalize_coordinates(x: float, y: float) -> Tuple[int, int]:
    """
    Normalize pixel coordinates to 0-1000 scale.
    
    Args:
        x: Pixel x coordinate
        y: Pixel y coordinate
        
    Returns:
        Tuple of (normalized_x, normalized_y) in 0-1000 range
    """
    norm_x = int((x / SCREEN_WIDTH) * 1000)
    norm_y = int((y / SCREEN_HEIGHT) * 1000)
    return (norm_x, norm_y)


def extract_interactive_elements(page: Page, limit: int = 50) -> List[Dict]:
    """
    Extract interactive elements (buttons, links, inputs) with their coordinates.
    
    Args:
        page: Playwright page object
        limit: Maximum number of elements to extract
        
    Returns:
        List of element dictionaries with type, text, id, and normalized coordinates
    """
    try:
        # JavaScript to extract interactive elements
        js_code = """
        () => {
            const elements = [];
            const selectors = [
                'button:visible',
                'a:visible',
                'input:visible',
                'textarea:visible',
                'select:visible',
                '[role="button"]:visible',
                '[role="link"]:visible',
                '[onclick]:visible'
            ];
            
            const seen = new Set();
            
            for (const selector of selectors) {
                const nodes = document.querySelectorAll(selector);
                for (const node of nodes) {
                    if (elements.length >= 50) break;
                    
                    const rect = node.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    
                    const key = `${rect.left},${rect.top}`;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    
                    elements.push({
                        type: node.tagName.toLowerCase(),
                        text: (node.innerText || node.value || node.placeholder || '').trim().substring(0, 50),
                        id: node.id || '',
                        className: node.className || '',
                        x: Math.round(centerX),
                        y: Math.round(centerY),
                        role: node.getAttribute('role') || ''
                    });
                }
            }
            
            return elements;
        }
        """
        
        elements = page.evaluate(js_code)
        
        # Normalize coordinates
        for elem in elements[:limit]:
            norm_x, norm_y = normalize_coordinates(elem["x"], elem["y"])
            elem["norm_x"] = norm_x
            elem["norm_y"] = norm_y
        
        return elements[:limit]
        
    except Exception as e:
        print(f"     ⚠️  DOM extraction failed: {e}")
        return []


def extract_accessibility_tree(page: Page) -> Optional[str]:
    """
    Extract accessibility tree snapshot from the page.
    
    Args:
        page: Playwright page object
        
    Returns:
        Accessibility tree as formatted string, or None if extraction fails
    """
    try:
        # Get accessibility snapshot
        snapshot = page.accessibility.snapshot()
        if not snapshot:
            return None
        
        # Format as readable text
        return _format_accessibility_node(snapshot, indent=0, max_depth=3)
        
    except Exception as e:
        print(f"     ⚠️  Accessibility tree extraction failed: {e}")
        return None


def _format_accessibility_node(node: Dict, indent: int = 0, max_depth: int = 3) -> str:
    """Format accessibility tree node recursively."""
    if indent > max_depth:
        return ""
    
    lines = []
    prefix = "  " * indent
    
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")
    
    if role:
        line = f"{prefix}{role}"
        if name:
            line += f": {name[:50]}"
        if value:
            line += f" = {value[:30]}"
        lines.append(line)
    
    # Process children
    children = node.get("children", [])
    for child in children[:10]:  # Limit children to avoid huge trees
        child_text = _format_accessibility_node(child, indent + 1, max_depth)
        if child_text:
            lines.append(child_text)
    
    return "\n".join(lines)


def build_element_map(page: Page) -> str:
    """
    Build a comprehensive element map with coordinates for the model.
    
    Args:
        page: Playwright page object
        
    Returns:
        Formatted string with interactive elements and their coordinates
    """
    elements = extract_interactive_elements(page)
    
    if not elements:
        return "No interactive elements detected."
    
    lines = ["INTERACTIVE ELEMENTS (normalized coordinates 0-1000):"]
    
    for i, elem in enumerate(elements, 1):
        elem_type = elem.get("type", "unknown")
        text = elem.get("text", "")
        norm_x = elem.get("norm_x", 0)
        norm_y = elem.get("norm_y", 0)
        elem_id = elem.get("id", "")
        
        # Format element info
        info = f"{i}. {elem_type.upper()}"
        if text:
            info += f" '{text}'"
        if elem_id:
            info += f" (id={elem_id})"
        info += f" @ ({norm_x}, {norm_y})"
        
        lines.append(info)
    
    return "\n".join(lines)


def format_dom_hints(page: Page, include_accessibility: bool = False) -> str:
    """
    Format DOM metadata as text hints for the model.
    
    Args:
        page: Playwright page object
        include_accessibility: Whether to include full accessibility tree
        
    Returns:
        Formatted DOM hints as string
    """
    hints = []
    
    # Add element map
    element_map = build_element_map(page)
    hints.append(element_map)
    
    # Optionally add accessibility tree
    if include_accessibility:
        acc_tree = extract_accessibility_tree(page)
        if acc_tree:
            hints.append("\nACCESSIBILITY TREE:")
            hints.append(acc_tree)
    
    return "\n\n".join(hints)
