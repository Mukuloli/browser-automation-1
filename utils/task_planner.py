"""
Task Planner Module for Browser Automation.

This module converts natural language user goals into structured, step-by-step
execution plans using Gemini AI. Each plan contains atomic browser actions
that can be validated visually.
"""

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from google.genai.types import Content, Part

from config import client


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Step:
    """
    Represents a single step in the execution plan.
    
    Attributes:
        step_num: Sequential step number
        action: Action type (navigate, click, type, scroll, wait, search)
        description: Human-readable description
        target: URL or element description
        value: Text to type or search query
        expected_result: Visual description for validation
    """
    
    step_num: int
    action: str
    description: str
    target: Optional[str] = None
    value: Optional[str] = None
    expected_result: str = ""
    
    # Compatibility aliases
    @property
    def num(self) -> int:
        """Alias for step_num."""
        return self.step_num
    
    @property
    def desc(self) -> str:
        """Alias for description."""
        return self.description
    
    @property
    def expected(self) -> str:
        """Alias for expected_result."""
        return self.expected_result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TaskPlan:
    """
    Complete execution plan for a browser automation task.
    
    Attributes:
        goal: Original user goal
        steps: List of execution steps
        success_criteria: How to determine task completion
    """
    
    goal: str
    steps: List[Step]
    success_criteria: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "success_criteria": self.success_criteria,
        }


# =============================================================================
# Planner Prompt
# =============================================================================

PLANNER_PROMPT = """You are a browser automation task planner. Convert the user's goal into a detailed step-by-step execution plan.

USER GOAL: {goal}

Generate a JSON plan with this EXACT structure:
{{
    "goal": "The user's goal restated clearly",
    "steps": [
        {{
            "step_num": 1,
            "action": "navigate|click|type|scroll|wait|search",
            "description": "What this step does in plain language",
            "target": "URL or element description (if applicable)",
            "value": "Text to type or search query (if applicable)",
            "expected_result": "What should be visible after this step succeeds"
        }}
    ],
    "success_criteria": "How to know the entire task completed successfully"
}}

RULES:
1. Break down complex tasks into simple, atomic steps
2. Each step should have ONE clear action
3. Always start with navigation to the right website
4. Include expected_result for visual validation
5. Use descriptive targets (e.g., "search box at top of page" not just "input")
6. Maximum 10 steps for any task

Return ONLY valid JSON, no markdown or explanation."""


# =============================================================================
# Task Planner
# =============================================================================

class TaskPlanner:
    """
    Generates step-by-step execution plans from natural language goals.
    
    Uses Gemini Flash model for fast plan generation.
    """
    
    MODEL = "gemini-2.5-flash"
    
    def __init__(self) -> None:
        """Initialize the task planner."""
        pass
    
    def plan(self, goal: str) -> TaskPlan:
        """
        Convert a user goal into a structured execution plan.
        
        Args:
            goal: Natural language task description
            
        Returns:
            TaskPlan with steps to execute
        """
        prompt = PLANNER_PROMPT.format(goal=goal)
        
        response = client.models.generate_content(
            model=self.MODEL,
            contents=[Content(role="user", parts=[Part(text=prompt)])],
        )
        
        return self._parse_response(response.text, goal)
    
    def _parse_response(self, text: str, goal: str) -> TaskPlan:
        """Parse JSON response into TaskPlan."""
        try:
            # Clean markdown code blocks
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            plan_data = json.loads(text)
            return self._build_plan(plan_data, goal)
            
        except json.JSONDecodeError as error:
            print(f"⚠️ Failed to parse plan JSON: {error}")
            print(f"   Raw response: {text[:200]}...")
            return self._fallback_plan(goal)
    
    def _build_plan(self, data: Dict[str, Any], goal: str) -> TaskPlan:
        """Build TaskPlan from parsed JSON data."""
        steps = []
        for idx, s in enumerate(data.get("steps", [])):
            steps.append(Step(
                step_num=s.get("step_num", idx + 1),
                action=s.get("action", "unknown"),
                description=s.get("description", ""),
                target=s.get("target"),
                value=s.get("value"),
                expected_result=s.get("expected_result", ""),
            ))
        
        return TaskPlan(
            goal=data.get("goal", goal),
            steps=steps,
            success_criteria=data.get("success_criteria", "Task completed"),
        )
    
    def _fallback_plan(self, goal: str) -> TaskPlan:
        """Return minimal fallback plan on parse failure."""
        return TaskPlan(
            goal=goal,
            steps=[
                Step(
                    step_num=1,
                    action="navigate",
                    description="Open browser and navigate to complete the task",
                    target="https://www.google.com",
                    expected_result="Google homepage loaded",
                )
            ],
            success_criteria="Task attempted",
        )
    
    def print_plan(self, plan: TaskPlan) -> None:
        """Pretty print an execution plan."""
        print("\n" + "=" * 60)
        print("📋 EXECUTION PLAN")
        print("=" * 60)
        print(f"\n🎯 Goal: {plan.goal}\n")
        
        for step in plan.steps:
            print(f"  Step {step.step_num}: {step.action.upper()}")
            print(f"    📝 {step.description}")
            if step.target:
                print(f"    🎯 Target: {step.target}")
            if step.value:
                print(f"    📝 Value: {step.value}")
            print(f"    ✓ Expected: {step.expected_result}")
            print()
        
        print(f"🏆 Success Criteria: {plan.success_criteria}")
        print("=" * 60 + "\n")
