"""
Safety Policy Module for Browser Automation.

This module enforces security rules to prevent dangerous browser automation actions.
It blocks specific domains, keywords, and tracks session limits.

Key Features:
    - Blocked domains (payment processors, banking, crypto)
    - Blocked action keywords (payments, account deletion, sensitive data)
    - Session scope limits (max actions, tokens, timeout)
    - Emergency stop functionality
    - Violation logging to JSON file
"""

import fnmatch
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Constants
# =============================================================================

SAFETY_LOG_FILE = os.path.join(os.path.dirname(__file__), "safety_log.json")

BLOCKED_DOMAINS: List[str] = [
    # Payment processors
    "paypal.com",
    "*.paypal.com",
    "stripe.com",
    "*.stripe.com",
    "razorpay.com",
    "*.razorpay.com",
    "paytm.com",
    "*.paytm.com",
    "checkout.stripe.com",
    # Banking
    "*bank*",
    "*banking*",
    "*.icicibank.com",
    "*.hdfcbank.com",
    "*.sbi.co.in",
    "*.chase.com",
    "*.wellsfargo.com",
    "*.bankofamerica.com",
    # Sensitive accounts
    "account.google.com/delete",
    "myaccount.google.com/delete",
    # Crypto
    "*.binance.com",
    "*.coinbase.com",
    "*.kraken.com",
]

BLOCKED_KEYWORDS: List[str] = [
    # Payment actions
    "pay now",
    "make payment",
    "checkout",
    "place order",
    "confirm purchase",
    "buy now",
    "add to cart and checkout",
    "enter card",
    "credit card",
    "debit card",
    "cvv",
    # Destructive actions
    "delete account",
    "delete all",
    "remove permanently",
    "cancel subscription",
    "unsubscribe all",
    "factory reset",
    "format drive",
    # Sensitive info
    "enter password",
    "change password",
    "reset password",
    "enter otp",
    "enter pin",
    "social security",
    # Financial
    "transfer money",
    "send money",
    "withdraw",
    "bitcoin",
    "crypto",
    "wallet address",
]

BLOCKED_URL_PATTERNS: List[str] = [
    "*checkout*",
    "*payment*",
    "*pay*",
    "*cart/checkout*",
    "*order/confirm*",
    "*delete*account*",
    "*close*account*",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SafetyViolation:
    """Records a safety violation event."""
    
    timestamp: str
    violation_type: str
    action: str
    url: Optional[str]
    details: str
    blocked: bool = True


@dataclass
class SessionScope:
    """Defines allowed scope and limits for a session."""
    
    allowed_domains: List[str] = field(default_factory=list)
    max_actions: int = 100
    max_tokens: int = 200000
    timeout_minutes: int = 30
    require_step_confirmation: bool = False


# =============================================================================
# Safety Policy
# =============================================================================

class SafetyPolicy:
    """
    Enforces safety rules for browser automation.
    
    Checks actions against blocked domains, keywords, and session limits.
    Logs all violations for audit purposes.
    """
    
    def __init__(self, scope: Optional[SessionScope] = None) -> None:
        """Initialize with optional session scope."""
        self.scope = scope or SessionScope()
        self.action_count = 0
        self.token_count = 0
        self.violations: List[SafetyViolation] = []
        self.start_time = datetime.now()
    
    def check_safety(
        self,
        action: str,
        url: str = "",
        target_text: str = "",
    ) -> Tuple[bool, str]:
        """
        Perform comprehensive safety check.
        
        Args:
            action: Action description
            url: Target URL (if applicable)
            target_text: Additional context text
            
        Returns:
            Tuple of (is_safe, reason)
        """
        # Check domain
        blocked, reason = self._is_domain_blocked(url)
        if blocked:
            self._log_violation("blocked_domain", action, url, reason)
            return False, reason
        
        # Check action keywords
        blocked, reason = self._is_action_blocked(action, target_text)
        if blocked:
            self._log_violation("blocked_keyword", action, url, reason)
            return False, reason
        
        # Check scope
        if url:
            in_scope, reason = self._is_in_scope(url)
            if not in_scope:
                self._log_violation("scope_exceeded", action, url, reason)
                return False, reason
        
        # Check limits
        within_limits, reason = self._check_limits()
        if not within_limits:
            self._log_violation("limit_exceeded", action, url, reason)
            return False, reason
        
        return True, ""
    
    def record_action(self, tokens_used: int = 0) -> None:
        """Record an action for limit tracking."""
        self.action_count += 1
        self.token_count += tokens_used
    
    def get_summary(self) -> Dict:
        """Get safety summary for the session."""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        return {
            "actions_executed": self.action_count,
            "tokens_used": self.token_count,
            "violations_blocked": len(self.violations),
            "session_duration_minutes": elapsed,
        }
    
    def _is_domain_blocked(self, url: str) -> Tuple[bool, str]:
        """Check if URL's domain is blocked."""
        if not url:
            return False, ""
        
        url_lower = url.lower()
        
        for pattern in BLOCKED_DOMAINS:
            if self._match_pattern(url_lower, pattern):
                return True, f"Domain matches blocked pattern: {pattern}"
        
        for pattern in BLOCKED_URL_PATTERNS:
            if fnmatch.fnmatch(url_lower, pattern):
                return True, f"URL matches blocked pattern: {pattern}"
        
        return False, ""
    
    def _is_action_blocked(self, action: str, target_text: str = "") -> Tuple[bool, str]:
        """Check if action contains blocked keywords."""
        combined = f"{action} {target_text}".lower()
        
        for keyword in BLOCKED_KEYWORDS:
            if keyword.lower() in combined:
                return True, f"Action contains blocked keyword: {keyword}"
        
        return False, ""
    
    def _is_in_scope(self, url: str) -> Tuple[bool, str]:
        """Check if URL is within allowed scope."""
        if not self.scope.allowed_domains:
            return True, ""
        
        url_lower = url.lower()
        for domain in self.scope.allowed_domains:
            if self._match_pattern(url_lower, f"*{domain}*"):
                return True, ""
        
        return False, f"URL not in allowed scope: {self.scope.allowed_domains}"
    
    def _check_limits(self) -> Tuple[bool, str]:
        """Check if session limits are exceeded."""
        if self.action_count >= self.scope.max_actions:
            return False, f"Max actions exceeded: {self.action_count}/{self.scope.max_actions}"
        
        if self.token_count >= self.scope.max_tokens:
            return False, f"Max tokens exceeded: {self.token_count}/{self.scope.max_tokens}"
        
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        if elapsed >= self.scope.timeout_minutes:
            return False, f"Session timeout: {elapsed:.1f}/{self.scope.timeout_minutes} min"
        
        return True, ""
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Match text against wildcard pattern."""
        regex = pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.search(regex, text))
    
    def _log_violation(
        self,
        violation_type: str,
        action: str,
        url: str,
        details: str,
    ) -> None:
        """Log a safety violation."""
        violation = SafetyViolation(
            timestamp=datetime.now().isoformat(),
            violation_type=violation_type,
            action=action,
            url=url,
            details=details,
        )
        self.violations.append(violation)
        self._save_to_log(violation)
        
        print(f"\n🛑 SAFETY VIOLATION BLOCKED!")
        print(f"   Type: {violation_type}")
        print(f"   Action: {action}")
        print(f"   Reason: {details}")
    
    def _save_to_log(self, violation: SafetyViolation) -> None:
        """Persist violation to log file."""
        try:
            if os.path.exists(SAFETY_LOG_FILE):
                with open(SAFETY_LOG_FILE, "r", encoding="utf-8") as f:
                    log = json.load(f)
            else:
                log = {"violations": []}
            
            log["violations"].append(asdict(violation))
            
            with open(SAFETY_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(log, f, indent=2)
        except Exception as error:
            print(f"⚠️ Failed to save safety log: {error}")


# =============================================================================
# Emergency Stop
# =============================================================================

_EMERGENCY_STOP = False


def trigger_emergency_stop() -> None:
    """Trigger emergency stop for all operations."""
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = True
    print("\n" + "🚨" * 20)
    print("🚨 EMERGENCY STOP TRIGGERED!")
    print("🚨" * 20 + "\n")


def is_emergency_stopped() -> bool:
    """Check if emergency stop is active."""
    return _EMERGENCY_STOP


def reset_emergency_stop() -> None:
    """Reset emergency stop flag."""
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = False
