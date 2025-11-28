"""Orchestrator module for research flows and planner agent.

This module provides:
- PlannerAgent: Creates report plans with sections
- IterativeResearchFlow: Single research loop pattern
- DeepResearchFlow: Parallel research loops pattern
- GraphOrchestrator: Stub for Phase 4 (uses agent chains for now)
- Protocols: SearchHandlerProtocol, JudgeHandlerProtocol (re-exported from legacy_orchestrator)
- Orchestrator: Legacy orchestrator class (re-exported from legacy_orchestrator)
"""

from typing import TYPE_CHECKING

# Re-export protocols and Orchestrator from legacy_orchestrator for backward compatibility
from src.legacy_orchestrator import (
    JudgeHandlerProtocol,
    Orchestrator,
    SearchHandlerProtocol,
)

# Lazy imports to avoid circular dependencies
if TYPE_CHECKING:
    from src.orchestrator.graph_orchestrator import GraphOrchestrator
    from src.orchestrator.planner_agent import PlannerAgent, create_planner_agent
    from src.orchestrator.research_flow import (
        DeepResearchFlow,
        IterativeResearchFlow,
    )

# Public exports
from src.orchestrator.graph_orchestrator import (
    GraphOrchestrator,
    create_graph_orchestrator,
)
from src.orchestrator.planner_agent import PlannerAgent, create_planner_agent
from src.orchestrator.research_flow import DeepResearchFlow, IterativeResearchFlow

__all__ = [
    "DeepResearchFlow",
    "GraphOrchestrator",
    "IterativeResearchFlow",
    "JudgeHandlerProtocol",
    "Orchestrator",
    "PlannerAgent",
    "SearchHandlerProtocol",
    "create_graph_orchestrator",
    "create_planner_agent",
]
