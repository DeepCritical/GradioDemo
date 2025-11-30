"""Unit tests for graph orchestrator factory integration."""

from typing import Any

import pytest

from src.agent_factory.judges import MockJudgeHandler
from src.orchestrator_factory import create_orchestrator
from src.orchestrator.graph_orchestrator import GraphOrchestrator
from src.tools.search_handler import SearchHandler
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.pubmed import PubMedTool
from src.utils.models import OrchestratorConfig


class MockSearchHandler:
    """Mock search handler for testing."""

    async def execute(self, query: str, max_results_per_tool: int = 10) -> Any:
        """Mock execute method."""
        from src.utils.models import Evidence, SearchResult

        return SearchResult(
            query=query,
            evidence=[],
            sources_searched=["pubmed"],
            total_found=0,
        )


def test_create_graph_orchestrator_with_handlers() -> None:
    """Test that graph orchestrator is created with handlers."""
    search_handler = SearchHandler(
        tools=[PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()],
        timeout=30.0,
    )
    judge_handler = MockJudgeHandler()
    config = OrchestratorConfig(max_iterations=5, max_results_per_tool=10)

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode="iterative",
    )

    assert isinstance(orchestrator, GraphOrchestrator)
    assert orchestrator.search_handler is not None
    assert orchestrator.judge_handler is not None
    assert orchestrator.mode == "iterative"


def test_create_graph_orchestrator_deep_mode() -> None:
    """Test that graph orchestrator is created in deep mode."""
    search_handler = SearchHandler(
        tools=[PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()],
        timeout=30.0,
    )
    judge_handler = MockJudgeHandler()
    config = OrchestratorConfig(max_iterations=5, max_results_per_tool=10)

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode="deep",
    )

    assert isinstance(orchestrator, GraphOrchestrator)
    assert orchestrator.mode == "deep"


def test_create_graph_orchestrator_auto_mode() -> None:
    """Test that graph orchestrator is created in auto mode."""
    search_handler = SearchHandler(
        tools=[PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()],
        timeout=30.0,
    )
    judge_handler = MockJudgeHandler()
    config = OrchestratorConfig(max_iterations=5, max_results_per_tool=10)

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode="auto",
    )

    assert isinstance(orchestrator, GraphOrchestrator)
    assert orchestrator.mode == "auto"

