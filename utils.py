"""Utils - Core helpers"""
import re, fnmatch, json, os, time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from playwright.sync_api import Page
from google.genai.types import Content, Part
from config import client, SCREEN_WIDTH, SCREEN_HEIGHT, BLOCKED_DOMAINS, BLOCKED_KEYWORDS

# ============ HELPERS ============
def denormalize_x(x): return int(x * SCREEN_WIDTH / 1000) if x <= 1000 else int(x)
def denormalize_y(y): return int(y * SCREEN_HEIGHT / 1000) if y <= 1000 else int(y)
def print_header(t): print(f"\n{'='*60}\n{t}\n{'='*60}")
def print_step(n): print(f"\n--- Step {n} ---")

# ============ SAFETY ============
SAFETY_LOG = os.path.join(os.path.dirname(__file__), "safety_log.json")
EMERGENCY_STOP = False

def is_blocked(url: str, action: str) -> Tuple[bool, str]:
    """Check if action/url is blocked."""
    combined = f"{url} {action}".lower()
    for p in BLOCKED_DOMAINS:
        if fnmatch.fnmatch(combined, f"*{p}*"): return True, f"Blocked: {p}"
    for k in BLOCKED_KEYWORDS:
        if k in combined: return True, f"Blocked keyword: {k}"
    return False, ""

def log_violation(action: str, reason: str):
    """Log blocked action."""
    try:
        log = json.load(open(SAFETY_LOG)) if os.path.exists(SAFETY_LOG) else {"violations": []}
        log["violations"].append({"time": datetime.now().isoformat(), "action": action, "reason": reason})
        json.dump(log, open(SAFETY_LOG, "w"), indent=2)
    except: pass

def trigger_stop(): global EMERGENCY_STOP; EMERGENCY_STOP = True; print("\n🚨 EMERGENCY STOP!")
def is_stopped(): return EMERGENCY_STOP
def reset_stop(): global EMERGENCY_STOP; EMERGENCY_STOP = False

# ============ ACTIONS ============
def execute_action(page: Page, fname: str, args: Dict) -> Dict:
    """Execute browser action with safety check."""
    url = args.get("url", page.url if not page.is_closed() else "")
    blocked, reason = is_blocked(url, f"{fname} {args}")
    if blocked:
        log_violation(f"{fname} {args}", reason)
        print(f"🛑 {reason}")
        return {"success": False, "blocked": True, "error": reason}
    
    try:
        if fname == "open_web_browser": page.goto("https://google.com"); return {"success": True}
        if fname in ["navigate", "go_to_url"]: page.goto(args.get("url", "https://google.com")); return {"success": True}
        if fname == "click_at":
            x, y = denormalize_x(args.get("x", 0)), denormalize_y(args.get("y", 0))
            page.mouse.click(x, y); return {"success": True}
        if fname == "type_text_at":
            x, y = denormalize_x(args.get("x", 0)), denormalize_y(args.get("y", 0))
            page.mouse.click(x, y); time.sleep(0.1)
            page.keyboard.press("Control+A"); page.keyboard.press("Backspace")
            page.keyboard.type(args.get("text", ""), delay=30)
            if args.get("press_enter"): page.keyboard.press("Enter")
            return {"success": True}
        if fname == "type_text": page.keyboard.type(args.get("text", ""), delay=30); return {"success": True}
        if fname in ["press_key", "key"]: page.keyboard.press(args.get("key", "Enter")); return {"success": True}
        if fname == "scroll": page.mouse.wheel(args.get("delta_x", 0), args.get("delta_y", 300)); return {"success": True}
        if fname == "go_back": page.go_back(); return {"success": True}
        if fname == "wait": time.sleep(float(args.get("duration", 1))); return {"success": True}
        return {"success": False, "error": f"Unknown: {fname}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_function_calls(candidate, page: Page) -> List:
    """Execute all function calls from response."""
    results = []
    for part in candidate.content.parts:
        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            print(f"  → {fc.name}")
            results.append((fc.name, execute_action(page, fc.name, dict(fc.args) if fc.args else {})))
            try: page.wait_for_load_state("domcontentloaded", timeout=3000)
            except: pass
            time.sleep(0.3)
    return results

def has_function_calls(c) -> bool:
    return any(hasattr(p, 'function_call') and p.function_call for p in c.content.parts)

def get_text_response(c) -> str:
    return " ".join(p.text for p in c.content.parts if hasattr(p, 'text') and p.text)

# ============ PLANNER ============
@dataclass
class Step:
    num: int; action: str; desc: str; target: str = ""; value: str = ""; expected: str = ""

@dataclass
class Plan:
    goal: str; steps: List[Step]; success: str

def generate_plan(goal: str) -> Plan:
    """Generate execution plan from goal."""
    prompt = f"""Convert to JSON plan:
GOAL: {goal}
FORMAT: {{"goal":"..","steps":[{{"num":1,"action":"navigate|click|type|search","desc":"..","target":"..","value":"..","expected":".."}}],"success":".."}}
Max 10 steps. Return ONLY JSON."""
    
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=[Content(role="user", parts=[Part(text=prompt)])])
    try:
        text = resp.text.strip()
        if text.startswith("```"): text = text.split("```")[1].replace("json", "", 1).strip()
        data = json.loads(text)
        return Plan(goal=data.get("goal", goal), 
                   steps=[Step(s.get("num", i+1), s.get("action", ""), s.get("desc", ""), s.get("target", ""), s.get("value", ""), s.get("expected", "")) for i, s in enumerate(data.get("steps", []))],
                   success=data.get("success", "Done"))
    except:
        return Plan(goal, [Step(1, "navigate", "Open browser", "google.com", "", "Page loaded")], "Attempted")

# ============ VALIDATOR ============
ERROR_DIR = os.path.join(os.path.dirname(__file__), "error_screenshots")
os.makedirs(ERROR_DIR, exist_ok=True)

@dataclass
class ValidationResult:
    ok: bool; reason: str; confidence: float; error_type: Optional[str] = None

def validate_step(screenshot: bytes, expected: str) -> ValidationResult:
    """Validate step with vision."""
    prompt = f"""Check screenshot matches: {expected}
Return JSON: {{"success":true/false,"reason":"..","confidence":0.0-1.0,"error_type":null/"captcha"/"error_page"/"blocked"}}"""
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=[Content(role="user", parts=[Part(text=prompt), Part.from_bytes(data=screenshot, mime_type="image/png")])])
        text = resp.text.strip()
        if text.startswith("```"): text = text.split("```")[1].replace("json", "", 1).strip()
        r = json.loads(text)
        return ValidationResult(r.get("success", False), r.get("reason", "Unknown"), r.get("confidence", 0.5), r.get("error_type"))
    except:
        return ValidationResult(False, "Parse error", 0, "unexpected")

def save_error(screenshot: bytes, step: int, error: str, reason: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(ERROR_DIR, f"error_{ts}_step{step}.png")
    open(path, "wb").write(screenshot)
    json.dump({"step": step, "error": error, "reason": reason}, open(path.replace(".png", ".json"), "w"))
    return path

# ============ CONFIRMATION ============
def confirm_plan(plan: Plan) -> str:
    """Show plan and get approval. Returns 'yes'/'step'/'no'."""
    print(f"\n{'='*50}\n⚠️ PLAN PREVIEW\n{'='*50}")
    print(f"Goal: {plan.goal}\n")
    for s in plan.steps:
        print(f"  {s.num}. {s.action.upper()}: {s.desc}")
        if s.target: print(f"     → {s.target}")
    print(f"\n🚨 Press Ctrl+C anytime to stop\n{'='*50}")
    choice = input("[Y]es / [S]tep-by-step / [N]o: ").strip().upper()
    return 'yes' if choice in ['Y', 'YES'] else 'step' if choice in ['S', 'STEP'] else 'no'

def confirm_step(step: Step) -> bool:
    """Confirm single step."""
    print(f"\n  Step {step.num}: {step.action} - {step.desc}")
    return input("  [Y/S/C]: ").strip().upper() in ['Y', 'YES', '']
