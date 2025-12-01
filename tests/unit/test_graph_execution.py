"""Unit tests for graph execution with handlers."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent_factory.judges import MockJudgeHandler
from src.orchestrator.graph_orchestrator import GraphOrchestrator
from src.tools.search_handler import SearchHandler
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.pubmed import PubMedTool
from src.utils.models import Evidence, JudgeAssessment, SearchResult


@pytest.fixture
def mock_search_handler() -> MagicMock:
    """Create a mock search handler."""
    handler = MagicMock(spec=SearchHandler)
    handler.execute = AsyncMock(
        return_value=SearchResult(
            query="test query",
            evidence=[
                Evidence(
                    content="Test evidence",
                    citation={
                        "source": "pubmed",
                        "title": "Test Title",
                        "url": "https://example.com",
                        "date": "2024-01-01",
                        "authors": ["Test Author"],
                    },
                    relevance=0.8,
                )
            ],
            sources_searched=["pubmed"],
            total_found=1,
        )
    )
    return handler


@pytest.fixture
def mock_judge_handler() -> MagicMock:
    """Create a mock judge handler."""
    handler = MagicMock(spec=MockJudgeHandler)
    handler.assess = AsyncMock(
        return_value=JudgeAssessment(
            details={
                "mechanism_score": 7,
                "mechanism_reasoning": "Good mechanism",
                "clinical_evidence_score": 6,
                "clinical_reasoning": "Moderate evidence",
                "drug_candidates": ["Test Drug"],
                "key_findings": ["Finding 1"],
            },
            sufficient=True,
            confidence=0.8,
            recommendation="synthesize",
            reasoning="Evidence is sufficient",
        )
    )
    return handler


@pytest.mark.asyncio
async def test_execute_tools_uses_search_handler(
    mock_search_handler: MagicMock, mock_judge_handler: MagicMock
) -> None:
    """Test that execute_tools state node uses search_handler.execute()."""
    orchestrator = GraphOrchestrator(
        mode="iterative",
        max_iterations=5,
        max_time_minutes=10,
        use_graph=True,
        search_handler=mock_search_handler,
        judge_handler=mock_judge_handler,
    )

    # This test would require full graph execution setup
    # For now, we verify the handler is stored
    assert orchestrator.search_handler is not None
    assert orchestrator.search_handler == mock_search_handler


@pytest.mark.asyncio
async def test_knowledge_gap_uses_judge_handler(
    mock_search_handler: MagicMock, mock_judge_handler: MagicMock
) -> None:
    """Test that knowledge_gap agent node uses judge_handler.assess()."""
    orchestrator = GraphOrchestrator(
        mode="iterative",
        max_iterations=5,
        max_time_minutes=10,
        use_graph=True,
        search_handler=mock_search_handler,
        judge_handler=mock_judge_handler,
    )

    # This test would require full graph execution setup
    # For now, we verify the handler is stored
    assert orchestrator.judge_handler is not None
    assert orchestrator.judge_handler == mock_judge_handler

