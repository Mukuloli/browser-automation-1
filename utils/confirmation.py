"""
Confirmation Manager Module for Browser Automation.

This module handles user approval workflow for browser automation tasks.
It displays plan previews, requests confirmation, and provides emergency
stop functionality.
"""

import signal
import sys
from typing import TYPE_CHECKING

from colorama import Fore, Style, init

if TYPE_CHECKING:
    from .task_planner import Step, TaskPlan

# Initialize colorama for Windows
init()


# =============================================================================
# Confirmation Manager
# =============================================================================

class ConfirmationManager:
    """
    Manages user confirmation for browser automation tasks.
    
    Provides plan preview, approval requests, step-by-step confirmation,
    and sensitive action verification.
    """
    
    def __init__(self, require_step_confirmation: bool = False) -> None:
        """
        Initialize confirmation manager.
        
        Args:
            require_step_confirmation: Whether to confirm each step individually
        """
        self.require_step_confirmation = require_step_confirmation
        self.approved = False
    
    def show_plan_preview(self, plan: "TaskPlan") -> None:
        """
        Display execution plan for user review.
        
        Args:
            plan: TaskPlan object with steps to display
        """
        print("\n" + "=" * 70)
        print(f"{Fore.YELLOW}⚠️  EXECUTION PLAN PREVIEW - REVIEW BEFORE APPROVING{Style.RESET_ALL}")
        print("=" * 70)
        print(f"\n{Fore.CYAN}🎯 Goal:{Style.RESET_ALL} {plan.goal}\n")
        print(f"{Fore.WHITE}Steps to be executed:{Style.RESET_ALL}")
        print("-" * 50)
        
        for step in plan.steps:
            self._print_step(step)
        
        print("\n" + "-" * 50)
        print(f"{Fore.CYAN}🏆 Success Criteria:{Style.RESET_ALL} {plan.success_criteria}")
        print("=" * 70)
    
    def _print_step(self, step: "Step") -> None:
        """Print a single step with formatting."""
        print(f"\n  {Fore.GREEN}Step {step.step_num}:{Style.RESET_ALL} {step.action.upper()}")
        print(f"    📝 {step.description}")
        
        if step.target:
            sensitive_words = ["pay", "bank", "checkout", "delete"]
            if any(word in step.target.lower() for word in sensitive_words):
                print(f"    {Fore.RED}⚠️ Target: {step.target}{Style.RESET_ALL}")
            else:
                print(f"    🎯 Target: {step.target}")
        
        if step.value:
            print(f"    📝 Value: {step.value}")
    
    def show_safety_warnings(self, warnings: list) -> None:
        """Display safety warnings."""
        if not warnings:
            return
        
        print(f"\n{Fore.RED}{'⚠️ ' * 10}")
        print("SAFETY WARNINGS:")
        for warning in warnings:
            print(f"  ❌ {warning}")
        print(f"{'⚠️ ' * 10}{Style.RESET_ALL}\n")
    
    def request_approval(self, allow_step_mode: bool = True) -> str:
        """
        Request user approval to proceed.
        
        Args:
            allow_step_mode: Whether to offer step-by-step option
            
        Returns:
            'yes' for full approval, 'step' for step-by-step, 'no' for cancel
        """
        print(f"\n{Fore.YELLOW}{'─' * 50}")
        print("CONFIRMATION REQUIRED")
        print(f"{'─' * 50}{Style.RESET_ALL}")
        
        if allow_step_mode:
            return self._request_with_step_mode()
        return self._request_simple()
    
    def _request_with_step_mode(self) -> str:
        """Request approval with step-by-step option."""
        print(f"\n  {Fore.GREEN}[Y]{Style.RESET_ALL} Yes - Execute all steps")
        print(f"  {Fore.CYAN}[S]{Style.RESET_ALL} Step - Confirm each step individually")
        print(f"  {Fore.RED}[N]{Style.RESET_ALL} No - Cancel execution\n")
        
        while True:
            choice = input("Your choice [Y/S/N]: ").strip().upper()
            
            if choice in ("Y", "YES"):
                self.approved = True
                print(f"\n{Fore.GREEN}✅ Execution approved!{Style.RESET_ALL}\n")
                return "yes"
            
            if choice in ("S", "STEP"):
                self.approved = True
                self.require_step_confirmation = True
                print(f"\n{Fore.CYAN}✅ Step-by-step mode enabled!{Style.RESET_ALL}\n")
                return "step"
            
            if choice in ("N", "NO", ""):
                print(f"\n{Fore.RED}❌ Execution cancelled by user.{Style.RESET_ALL}\n")
                return "no"
            
            print(f"  {Fore.YELLOW}Please enter Y, S, or N{Style.RESET_ALL}")
    
    def _request_simple(self) -> str:
        """Simple yes/no approval request."""
        print(f"\n  {Fore.GREEN}[Y]{Style.RESET_ALL} Yes - Proceed")
        print(f"  {Fore.RED}[N]{Style.RESET_ALL} No - Cancel\n")
        
        while True:
            choice = input("Proceed? [Y/N]: ").strip().upper()
            
            if choice in ("Y", "YES"):
                self.approved = True
                return "yes"
            
            if choice in ("N", "NO", ""):
                return "no"
            
            print(f"  {Fore.YELLOW}Please enter Y or N{Style.RESET_ALL}")
    
    def request_step_approval(self, step: "Step") -> bool:
        """
        Request approval for a specific step.
        
        Args:
            step: Step to approve
            
        Returns:
            True if approved, False to skip
            
        Raises:
            KeyboardInterrupt: If user cancels execution
        """
        print(f"\n{Fore.CYAN}{'─' * 40}")
        print(f"STEP {step.step_num} CONFIRMATION")
        print(f"{'─' * 40}{Style.RESET_ALL}")
        print(f"  Action: {step.action.upper()}")
        print(f"  Description: {step.description}")
        if step.target:
            print(f"  Target: {step.target}")
        
        print()
        print(f"  {Fore.GREEN}[Y]{Style.RESET_ALL} Execute this step")
        print(f"  {Fore.YELLOW}[S]{Style.RESET_ALL} Skip this step")
        print(f"  {Fore.RED}[C]{Style.RESET_ALL} Cancel remaining execution\n")
        
        while True:
            choice = input("  Choice [Y/S/C]: ").strip().upper()
            
            if choice in ("Y", "YES", ""):
                return True
            
            if choice in ("S", "SKIP"):
                print(f"  {Fore.YELLOW}⏭️ Step skipped{Style.RESET_ALL}")
                return False
            
            if choice in ("C", "CANCEL"):
                print(f"  {Fore.RED}🛑 Execution cancelled{Style.RESET_ALL}")
                raise KeyboardInterrupt("User cancelled execution")
            
            print(f"  {Fore.YELLOW}Please enter Y, S, or C{Style.RESET_ALL}")
    
    def show_emergency_stop_instructions(self) -> None:
        """Display emergency stop instructions."""
        print(f"\n{Fore.RED}{'─' * 50}")
        print("🚨 EMERGENCY STOP: Press Ctrl+C at any time to halt")
        print(f"{'─' * 50}{Style.RESET_ALL}\n")
    
    def confirm_sensitive_action(self, action: str, details: str) -> bool:
        """
        Request explicit confirmation for sensitive action.
        
        Args:
            action: Action being performed
            details: Additional context
            
        Returns:
            True if confirmed, False otherwise
        """
        print(f"\n{Fore.RED}{'⚠️ ' * 15}")
        print("SENSITIVE ACTION DETECTED")
        print(f"{'⚠️ ' * 15}{Style.RESET_ALL}")
        print(f"\n  Action: {action}")
        print(f"  Details: {details}")
        print(f"\n  {Fore.RED}This action may have significant consequences!{Style.RESET_ALL}")
        
        confirm = input("\n  Type 'CONFIRM' to proceed, or anything else to cancel: ").strip()
        
        if confirm == "CONFIRM":
            print(f"  {Fore.YELLOW}⚠️ Action confirmed by user{Style.RESET_ALL}")
            return True
        
        print(f"  {Fore.GREEN}✅ Action cancelled{Style.RESET_ALL}")
        return False


# =============================================================================
# Emergency Stop Handler
# =============================================================================

def setup_emergency_stop_handler() -> None:
    """Set up signal handler for emergency stop (Ctrl+C)."""
    from .safety_policy import trigger_emergency_stop
    
    def handler(signum, frame):
        trigger_emergency_stop()
        print("\n\n🛑 Emergency stop activated! Cleaning up...")
        raise KeyboardInterrupt("Emergency stop triggered")
    
    signal.signal(signal.SIGINT, handler)
    
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, handler)
