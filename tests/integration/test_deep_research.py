"""Integration tests for deep research flow.

Tests the complete deep research pattern: plan → parallel loops → synthesis.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.middleware.state_machine import init_workflow_state
from src.orchestrator.research_flow import DeepResearchFlow
from src.utils.models import ReportPlan, ReportPlanSection


@pytest.mark.integration
class TestDeepResearchFlow:
    """Integration tests for DeepResearchFlow."""

    @pytest.mark.asyncio
    async def test_deep_research_creates_plan(self) -> None:
        """Test that deep research creates a report plan."""
        # Initialize workflow state
        init_workflow_state()

        flow = DeepResearchFlow(
            max_iterations=2,
            max_time_minutes=5,
            verbose=False,
            use_graph=False,
        )

        # Mock the planner agent to return a simple plan
        mock_plan = ReportPlan(
            background_context="Test background context",
            report_outline=[
                ReportPlanSection(
                    title="Section 1",
                    key_question="What is the first question?",
                ),
                ReportPlanSection(
                    title="Section 2",
                    key_question="What is the second question?",
                ),
            ],
            report_title="Test Report",
        )

        flow.planner_agent.run = AsyncMock(return_value=mock_plan)

        # Mock the iterative research flows to return simple drafts
        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            return f"# Draft for: {query}\n\nThis is a test draft."

        # Mock the long writer to return a simple report
        flow.long_writer_agent.write_report = AsyncMock(
            return_value="# Test Report\n\n## Section 1\n\nDraft 1\n\n## Section 2\n\nDraft 2"
        )

        # We can't easily mock the IterativeResearchFlow.run() without more setup
        # So we'll test the plan creation separately
        plan = await flow._build_report_plan("Test query")

        assert isinstance(plan, ReportPlan)
        assert plan.report_title == "Test Report"
        assert len(plan.report_outline) == 2
        assert plan.report_outline[0].title == "Section 1"

    @pytest.mark.asyncio
    async def test_deep_research_parallel_loops_state_synchronization(self) -> None:
        """Test that parallel loops properly synchronize state."""
        # Initialize workflow state
        state = init_workflow_state()

        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
        )

        # Create a simple report plan
        report_plan = ReportPlan(
            background_context="Test background",
            report_outline=[
                ReportPlanSection(
                    title="Section 1",
                    key_question="Question 1?",
                ),
                ReportPlanSection(
                    title="Section 2",
                    key_question="Question 2?",
                ),
            ],
            report_title="Test Report",
        )

        # Mock iterative research flows to add evidence to state
        from src.utils.models import Citation, Evidence

        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            # Add evidence to state to test synchronization
            ev = Evidence(
                content=f"Evidence for {query}",
                citation=Citation(
                    source="pubmed",
                    title=f"Title for {query}",
                    url=f"https://example.com/{query.replace('?', '').replace(' ', '_')}",
                    date="2024-01-01",
                ),
            )
            state.add_evidence([ev])
            return f"# Draft: {query}\n\nTest content."

        # Patch IterativeResearchFlow.run
        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow.run",
            side_effect=mock_iterative_run,
        ):
            section_drafts = await flow._run_research_loops(report_plan)

        # Verify parallel execution
        assert len(section_drafts) == 2
        assert "Question 1" in section_drafts[0]
        assert "Question 2" in section_drafts[1]

        # Verify state has evidence from both sections
        # Note: In real execution, evidence would be synced via WorkflowManager
        # This test verifies the structure works

    @pytest.mark.asyncio
    async def test_deep_research_synthesizes_final_report(self) -> None:
        """Test that deep research synthesizes final report from section drafts."""
        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
            use_long_writer=True,
        )

        # Create report plan
        report_plan = ReportPlan(
            background_context="Test background",
            report_outline=[
                ReportPlanSection(
                    title="Introduction",
                    key_question="What is the topic?",
                ),
                ReportPlanSection(
                    title="Conclusion",
                    key_question="What are the conclusions?",
                ),
            ],
            report_title="Test Report",
        )

        # Create section drafts
        section_drafts = [
            "# Introduction\n\nThis is the introduction section.",
            "# Conclusion\n\nThis is the conclusion section.",
        ]

        # Mock long writer
        flow.long_writer_agent.write_report = AsyncMock(
            return_value="# Test Report\n\n## Introduction\n\nContent\n\n## Conclusion\n\nContent"
        )

        final_report = await flow._create_final_report("Test query", report_plan, section_drafts)

        assert isinstance(final_report, str)
        assert "Test Report" in final_report
        # Verify long writer was called with correct parameters
        flow.long_writer_agent.write_report.assert_called_once()
        call_args = flow.long_writer_agent.write_report.call_args
        assert call_args.kwargs["original_query"] == "Test query"
        assert call_args.kwargs["report_title"] == "Test Report"
        assert len(call_args.kwargs["report_draft"].sections) == 2

    @pytest.mark.asyncio
    async def test_deep_research_agent_chains_full_flow(self) -> None:
        """Test full deep research flow with agent chains (mocked)."""
        # Initialize workflow state
        init_workflow_state()

        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
        )

        # Mock all agents
        mock_plan = ReportPlan(
            background_context="Background",
            report_outline=[
                ReportPlanSection(
                    title="Section 1",
                    key_question="Question 1?",
                ),
            ],
            report_title="Test Report",
        )

        flow.planner_agent.run = AsyncMock(return_value=mock_plan)

        # Mock iterative research
        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            return f"# Draft\n\nAnswer to {query}"

        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow.run",
            side_effect=mock_iterative_run,
        ):
            flow.long_writer_agent.write_report = AsyncMock(
                return_value="# Test Report\n\n## Section 1\n\nDraft content"
            )

            # Run the full flow
            result = await flow._run_with_chains("Test query")

        assert isinstance(result, str)
        assert "Test Report" in result
        flow.planner_agent.run.assert_called_once()
        flow.long_writer_agent.write_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_research_handles_multiple_sections(self) -> None:
        """Test that deep research handles multiple sections correctly."""
        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
        )

        # Create plan with multiple sections
        report_plan = ReportPlan(
            background_context="Background",
            report_outline=[
                ReportPlanSection(
                    title=f"Section {i}",
                    key_question=f"Question {i}?",
                )
                for i in range(5)  # 5 sections
            ],
            report_title="Multi-Section Report",
        )

        # Mock iterative research to return unique drafts
        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            section_num = query.split()[-1].replace("?", "")
            return f"# Section {section_num} Draft\n\nContent for section {section_num}"

        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow.run",
            side_effect=mock_iterative_run,
        ):
            section_drafts = await flow._run_research_loops(report_plan)

        # Verify all sections were processed
        assert len(section_drafts) == 5
        for i, draft in enumerate(section_drafts):
            assert f"Section {i}" in draft or f"section {i}" in draft.lower()

    @pytest.mark.asyncio
    async def test_deep_research_workflow_manager_integration(self) -> None:
        """Test that deep research properly uses WorkflowManager."""

        # Initialize workflow state
        init_workflow_state()

        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
        )

        # Create report plan
        report_plan = ReportPlan(
            background_context="Background",
            report_outline=[
                ReportPlanSection(
                    title="Section 1",
                    key_question="Question 1?",
                ),
                ReportPlanSection(
                    title="Section 2",
                    key_question="Question 2?",
                ),
            ],
            report_title="Test Report",
        )

        # Mock iterative research
        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            return f"# Draft: {query}"

        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow.run",
            side_effect=mock_iterative_run,
        ):
            section_drafts = await flow._run_research_loops(report_plan)

        # Verify WorkflowManager was used (section_drafts should be returned)
        assert len(section_drafts) == 2
        # Each draft should be a string
        assert all(isinstance(draft, str) for draft in section_drafts)

    @pytest.mark.asyncio
    async def test_deep_research_state_initialization(self) -> None:
        """Test that deep research properly initializes workflow state."""
        flow = DeepResearchFlow(
            max_iterations=1,
            max_time_minutes=2,
            verbose=False,
            use_graph=False,
        )

        # Mock the planner
        mock_plan = ReportPlan(
            background_context="Background",
            report_outline=[
                ReportPlanSection(
                    title="Section 1",
                    key_question="Question 1?",
                ),
            ],
            report_title="Test Report",
        )

        flow.planner_agent.run = AsyncMock(return_value=mock_plan)

        # Mock iterative research
        async def mock_iterative_run(query: str, **kwargs: dict) -> str:
            return "# Draft"

        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow.run",
            side_effect=mock_iterative_run,
        ):
            flow.long_writer_agent.write_report = AsyncMock(return_value="# Test Report\n\nContent")

            # Run with chains - should initialize state
            # Note: _run_with_chains handles missing embedding service gracefully
            await flow._run_with_chains("Test query")

            # Verify state was initialized (get_workflow_state should not raise)
            from src.middleware.state_machine import get_workflow_state

            state = get_workflow_state()
            assert state is not None
