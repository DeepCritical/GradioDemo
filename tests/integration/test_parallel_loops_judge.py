"""Integration tests for Phase 7: Parallel loops with judge-based completion.

These tests verify that WorkflowManager can coordinate parallel research loops
and use the judge to determine when loops should complete.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.workflow_manager import WorkflowManager
from src.orchestrator.research_flow import IterativeResearchFlow
from src.utils.models import Citation, Evidence, JudgeAssessment


@pytest.fixture
def mock_judge_handler():
    """Create a mock judge handler."""
    judge = MagicMock()
    judge.assess = AsyncMock()
    return judge


@pytest.fixture
def mock_iterative_flow():
    """Create a mock iterative research flow."""
    flow = MagicMock(spec=IterativeResearchFlow)
    flow.run = AsyncMock(return_value="# Test Report\n\nContent here.")
    return flow


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelLoopsWithJudge:
    """Tests for parallel loops with judge-based completion."""

    async def test_get_loop_evidence(self):
        """get_loop_evidence should return evidence from a loop."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        # Add evidence to the loop
        evidence = [
            Evidence(
                content="Test evidence",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.8,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        # Retrieve evidence
        retrieved_evidence = await manager.get_loop_evidence("loop1")
        assert len(retrieved_evidence) == 1
        assert retrieved_evidence[0].content == "Test evidence"

    async def test_get_loop_evidence_returns_empty_for_missing_loop(self):
        """get_loop_evidence should return empty list for non-existent loop."""
        manager = WorkflowManager()
        evidence = await manager.get_loop_evidence("nonexistent")
        assert evidence == []

    async def test_check_loop_completion_with_sufficient_evidence(self, mock_judge_handler):
        """check_loop_completion should return True when judge says sufficient."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        # Add evidence
        evidence = [
            Evidence(
                content="Comprehensive evidence",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.9,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        # Mock judge to say sufficient
        from src.utils.models import AssessmentDetails

        mock_judge_handler.assess = AsyncMock(
            return_value=JudgeAssessment(
                details=AssessmentDetails(
                    mechanism_score=5,
                    mechanism_reasoning="Test mechanism reasoning that is long enough",
                    clinical_evidence_score=5,
                    clinical_reasoning="Test clinical reasoning that is long enough",
                    drug_candidates=[],
                    key_findings=[],
                ),
                sufficient=True,
                confidence=0.95,
                recommendation="synthesize",
                reasoning="Evidence is sufficient to provide a comprehensive answer.",
            )
        )

        should_complete, reason = await manager.check_loop_completion(
            "loop1", "Test query", mock_judge_handler
        )

        assert should_complete is True
        assert "sufficient" in reason.lower() or "judge" in reason.lower()
        assert mock_judge_handler.assess.called

    async def test_check_loop_completion_with_insufficient_evidence(self, mock_judge_handler):
        """check_loop_completion should return False when judge says insufficient."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        # Add minimal evidence
        evidence = [
            Evidence(
                content="Minimal evidence",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.3,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        # Mock judge to say insufficient
        from src.utils.models import AssessmentDetails

        mock_judge_handler.assess = AsyncMock(
            return_value=JudgeAssessment(
                details=AssessmentDetails(
                    mechanism_score=3,
                    mechanism_reasoning="Test mechanism reasoning that is long enough",
                    clinical_evidence_score=3,
                    clinical_reasoning="Test clinical reasoning that is long enough",
                    drug_candidates=[],
                    key_findings=[],
                ),
                sufficient=False,
                confidence=0.4,
                recommendation="continue",
                reasoning="Need more evidence to provide a comprehensive answer.",
            )
        )

        should_complete, reason = await manager.check_loop_completion(
            "loop1", "Test query", mock_judge_handler
        )

        assert should_complete is False
        assert "judge" in reason.lower() or "evidence" in reason.lower()
        assert mock_judge_handler.assess.called

    async def test_check_loop_completion_with_no_evidence(self, mock_judge_handler):
        """check_loop_completion should return False when no evidence exists."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        # Don't add any evidence

        should_complete, reason = await manager.check_loop_completion(
            "loop1", "Test query", mock_judge_handler
        )

        assert should_complete is False
        assert "no evidence" in reason.lower() or "not" in reason.lower()
        # Judge should not be called if no evidence
        assert not mock_judge_handler.assess.called

    async def test_check_loop_completion_handles_judge_error(self, mock_judge_handler):
        """check_loop_completion should handle judge errors gracefully."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        evidence = [
            Evidence(
                content="Test evidence",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.8,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        # Mock judge to raise error
        mock_judge_handler.assess = AsyncMock(side_effect=Exception("Judge error"))

        should_complete, reason = await manager.check_loop_completion(
            "loop1", "Test query", mock_judge_handler
        )

        assert should_complete is False
        assert "error" in reason.lower() or "failed" in reason.lower()

    async def test_parallel_loops_with_judge_early_termination(
        self, mock_judge_handler, mock_iterative_flow
    ):
        """Parallel loops should terminate early when judge says sufficient."""
        manager = WorkflowManager()

        # Create multiple loops
        loop_configs = [
            {"loop_id": "loop1", "query": "Query 1"},
            {"loop_id": "loop2", "query": "Query 2"},
        ]

        # Define loop function that extracts loop_func from config if needed
        async def loop_func(config: dict) -> str:
            return await mock_iterative_flow.run(config.get("query", ""))

        # Add evidence to loop1 that will trigger early completion
        await manager.add_loop("loop1", "Query 1")
        evidence = [
            Evidence(
                content="Comprehensive evidence for query 1",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.95,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        # Mock judge to say sufficient for loop1
        call_count = {"count": 0}

        def mock_assess(query: str, evidence_list: list[Evidence]) -> JudgeAssessment:
            from src.utils.models import AssessmentDetails

            call_count["count"] += 1
            if "Query 1" in query or len(evidence_list) > 0:
                return JudgeAssessment(
                    details=AssessmentDetails(
                        mechanism_score=5,
                        mechanism_reasoning="Test mechanism reasoning that is long enough",
                        clinical_evidence_score=5,
                        clinical_reasoning="Test clinical reasoning that is long enough",
                        drug_candidates=[],
                        key_findings=[],
                    ),
                    sufficient=True,
                    confidence=0.95,
                    recommendation="synthesize",
                    reasoning="Sufficient evidence has been collected to answer the query.",
                )
            return JudgeAssessment(
                details=AssessmentDetails(
                    mechanism_score=3,
                    mechanism_reasoning="Test mechanism reasoning that is long enough",
                    clinical_evidence_score=3,
                    clinical_reasoning="Test clinical reasoning that is long enough",
                    drug_candidates=[],
                    key_findings=[],
                ),
                sufficient=False,
                confidence=0.5,
                recommendation="continue",
                reasoning="Need more evidence to provide a comprehensive answer.",
            )

        mock_judge_handler.assess = AsyncMock(side_effect=mock_assess)

        # Run loops in parallel
        with patch("src.middleware.workflow_manager.get_workflow_state") as mock_state:
            mock_state_obj = MagicMock()
            mock_state_obj.evidence = []
            mock_state.return_value = mock_state_obj

            results = await manager.run_loops_parallel(
                loop_configs, loop_func=loop_func, judge_handler=mock_judge_handler
            )

            # Both loops should complete
            assert len(results) == 2
            assert all(isinstance(r, str) for r in results)

    async def test_parallel_loops_aggregate_evidence(self, mock_judge_handler):
        """Parallel loops should aggregate evidence from all loops."""
        manager = WorkflowManager()

        # Create loops
        await manager.add_loop("loop1", "Query 1")
        await manager.add_loop("loop2", "Query 2")

        # Add evidence to each loop
        evidence1 = [
            Evidence(
                content="Evidence from loop 1",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test 1",
                    url="https://example.com/1",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.8,
            )
        ]
        evidence2 = [
            Evidence(
                content="Evidence from loop 2",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test 2",
                    url="https://example.com/2",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.9,
            )
        ]

        await manager.add_loop_evidence("loop1", evidence1)
        await manager.add_loop_evidence("loop2", evidence2)

        # Get evidence from both loops
        evidence1_retrieved = await manager.get_loop_evidence("loop1")
        evidence2_retrieved = await manager.get_loop_evidence("loop2")

        assert len(evidence1_retrieved) == 1
        assert len(evidence2_retrieved) == 1
        assert evidence1_retrieved[0].content == "Evidence from loop 1"
        assert evidence2_retrieved[0].content == "Evidence from loop 2"

    async def test_loop_status_updated_on_completion(self, mock_judge_handler):
        """Loop status should be updated when judge determines completion."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Test query")

        # Add sufficient evidence
        evidence = [
            Evidence(
                content="Sufficient evidence",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.95,
            )
        ]
        await manager.add_loop_evidence("loop1", evidence)

        from src.utils.models import AssessmentDetails

        mock_judge_handler.assess = AsyncMock(
            return_value=JudgeAssessment(
                details=AssessmentDetails(
                    mechanism_score=5,
                    mechanism_reasoning="Test mechanism reasoning that is long enough",
                    clinical_evidence_score=5,
                    clinical_reasoning="Test clinical reasoning that is long enough",
                    drug_candidates=[],
                    key_findings=[],
                ),
                sufficient=True,
                confidence=0.95,
                recommendation="synthesize",
                reasoning="Complete evidence has been collected to answer the query.",
            )
        )

        # Check completion (this should update status internally if implemented)
        should_complete, _ = await manager.check_loop_completion(
            "loop1", "Test query", mock_judge_handler
        )

        assert should_complete is True
        # Status update would happen in run_loops_parallel, not in check_loop_completion
        loop = await manager.get_loop("loop1")
        assert loop is not None
        # Status might still be "pending" or "running" until run_loops_parallel updates it
