"""Unit tests for ResearchFlow classes."""

from unittest.mock import AsyncMock, patch

import pytest

from src.orchestrator.research_flow import DeepResearchFlow, IterativeResearchFlow
from src.utils.models import (
    AgentSelectionPlan,
    AgentTask,
    KnowledgeGapOutput,
    ReportPlan,
    ReportPlanSection,
    ToolAgentOutput,
)


class TestIterativeResearchFlow:
    """Tests for IterativeResearchFlow."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for the flow."""
        return {
            "knowledge_gap": AsyncMock(),
            "tool_selector": AsyncMock(),
            "thinking": AsyncMock(),
            "writer": AsyncMock(),
        }

    @pytest.fixture
    def flow(self, mock_agents):
        """Create an IterativeResearchFlow with mocked agents."""
        with (
            patch("src.orchestrator.research_flow.create_knowledge_gap_agent") as mock_kg,
            patch("src.orchestrator.research_flow.create_tool_selector_agent") as mock_ts,
            patch("src.orchestrator.research_flow.create_thinking_agent") as mock_thinking,
            patch("src.orchestrator.research_flow.create_writer_agent") as mock_writer,
            patch("src.orchestrator.research_flow.execute_tool_tasks") as mock_execute,
        ):
            mock_kg.return_value = mock_agents["knowledge_gap"]
            mock_ts.return_value = mock_agents["tool_selector"]
            mock_thinking.return_value = mock_agents["thinking"]
            mock_writer.return_value = mock_agents["writer"]
            mock_execute.return_value = {
                "task_1": ToolAgentOutput(output="Finding 1", sources=["url1"]),
            }

            yield IterativeResearchFlow(max_iterations=2, max_time_minutes=5)

    @pytest.mark.asyncio
    async def test_iterative_flow_completes_when_research_complete(self, flow, mock_agents):
        """IterativeResearchFlow should complete when research is marked complete."""
        # Mock knowledge gap agent to return complete
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=True,
                outstanding_gaps=[],
            )
        )

        # Mock thinking agent
        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Initial thoughts")

        # Mock writer agent
        mock_agents["writer"].write_report = AsyncMock(
            return_value="# Final Report\n\nContent here."
        )

        result = await flow.run("Test query")

        assert isinstance(result, str)
        assert "Final Report" in result
        assert flow.iteration == 1  # Should complete after first iteration

    @pytest.mark.asyncio
    async def test_iterative_flow_loops_when_research_incomplete(self, flow, mock_agents):
        """IterativeResearchFlow should loop when research is incomplete."""
        # Mock knowledge gap agent to return incomplete, then complete
        call_count = {"count": 0}

        def mock_evaluate(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return KnowledgeGapOutput(
                    research_complete=False,
                    outstanding_gaps=["Need more info"],
                )
            return KnowledgeGapOutput(
                research_complete=True,
                outstanding_gaps=[],
            )

        mock_agents["knowledge_gap"].evaluate = AsyncMock(side_effect=mock_evaluate)

        # Mock thinking agent
        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")

        # Mock tool selector
        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Need more info",
                        agent="WebSearchAgent",
                        query="test query",
                    )
                ]
            )
        )

        # Mock writer
        mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nContent")

        result = await flow.run("Test query")

        assert isinstance(result, str)
        assert flow.iteration >= 1

    @pytest.mark.asyncio
    async def test_iterative_flow_respects_max_iterations(self, flow, mock_agents):
        """IterativeResearchFlow should stop at max_iterations."""
        # Always return incomplete
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["Gap 1"],
            )
        )

        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")

        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Gap 1",
                        agent="WebSearchAgent",
                        query="test",
                    )
                ]
            )
        )

        mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nContent")

        await flow.run("Test query")

        # Should stop at max_iterations (2)
        assert flow.iteration <= flow.max_iterations

    @pytest.mark.asyncio
    async def test_iterative_flow_handles_tool_execution_error(self, flow, mock_agents):
        """IterativeResearchFlow should handle tool execution errors gracefully."""
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["Gap 1"],
            )
        )

        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")

        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Gap 1",
                        agent="WebSearchAgent",
                        query="test",
                    )
                ]
            )
        )

        # Mock tool execution to fail
        with patch("src.orchestrator.research_flow.execute_tool_tasks") as mock_execute:
            mock_execute.side_effect = Exception("Tool execution failed")

            mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nContent")

            # Should not raise, should complete with report
            result = await flow.run("Test query")
            assert isinstance(result, str)


class TestDeepResearchFlow:
    """Tests for DeepResearchFlow."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for the flow."""
        return {
            "planner": AsyncMock(),
            "long_writer": AsyncMock(),
            "proofreader": AsyncMock(),
        }

    @pytest.fixture
    def flow(self, mock_agents):
        """Create a DeepResearchFlow with mocked agents."""
        with (
            patch("src.orchestrator.research_flow.create_planner_agent") as mock_planner,
            patch("src.orchestrator.research_flow.create_long_writer_agent") as mock_long_writer,
            patch("src.orchestrator.research_flow.create_proofreader_agent") as mock_proofreader,
        ):
            mock_planner.return_value = mock_agents["planner"]
            mock_long_writer.return_value = mock_agents["long_writer"]
            mock_proofreader.return_value = mock_agents["proofreader"]

            yield DeepResearchFlow(max_iterations=2, max_time_minutes=5)

    @pytest.mark.asyncio
    async def test_deep_flow_creates_report_plan(self, flow, mock_agents):
        """DeepResearchFlow should create a report plan."""
        mock_plan = ReportPlan(
            background_context="Context",
            report_outline=[
                ReportPlanSection(title="Section 1", key_question="Question 1?"),
                ReportPlanSection(title="Section 2", key_question="Question 2?"),
            ],
            report_title="Test Report",
        )

        mock_agents["planner"].run = AsyncMock(return_value=mock_plan)

        # Mock iterative flow results
        with patch("src.orchestrator.research_flow.IterativeResearchFlow") as mock_iterative:
            mock_iterative_instance = AsyncMock()
            mock_iterative_instance.run = AsyncMock(
                side_effect=["Section 1 content", "Section 2 content"]
            )
            mock_iterative.return_value = mock_iterative_instance

            mock_agents["long_writer"].write_report = AsyncMock(
                return_value="# Final Report\n\nContent"
            )

            result = await flow.run("Test query")

            assert isinstance(result, str)
            assert "Final Report" in result
            mock_agents["planner"].run.assert_called_once_with("Test query")

    @pytest.mark.asyncio
    async def test_deep_flow_runs_parallel_research_loops(self, flow, mock_agents):
        """DeepResearchFlow should run parallel research loops for each section."""
        mock_plan = ReportPlan(
            background_context="Context",
            report_outline=[
                ReportPlanSection(title="Section 1", key_question="Q1?"),
                ReportPlanSection(title="Section 2", key_question="Q2?"),
                ReportPlanSection(title="Section 3", key_question="Q3?"),
            ],
            report_title="Test Report",
        )

        mock_agents["planner"].run = AsyncMock(return_value=mock_plan)

        # Track calls to iterative flow
        iterative_calls = []

        def create_iterative_flow(*args, **kwargs):
            flow_instance = AsyncMock()
            flow_instance.run = AsyncMock(
                side_effect=lambda query, **kw: iterative_calls.append(query)
                or f"Content for {query}"
            )
            return flow_instance

        with patch(
            "src.orchestrator.research_flow.IterativeResearchFlow",
            side_effect=create_iterative_flow,
        ):
            mock_agents["long_writer"].write_report = AsyncMock(
                return_value="# Final Report\n\nContent"
            )

            await flow.run("Test query")

            # Should have called iterative flow for each section
            assert len(iterative_calls) == 3
            assert "Q1?" in iterative_calls
            assert "Q2?" in iterative_calls
            assert "Q3?" in iterative_calls

    @pytest.mark.asyncio
    async def test_deep_flow_uses_proofreader_when_specified(self, flow, mock_agents):
        """DeepResearchFlow should use proofreader when use_long_writer=False."""
        flow.use_long_writer = False

        mock_plan = ReportPlan(
            background_context="Context",
            report_outline=[
                ReportPlanSection(title="Section 1", key_question="Q1?"),
            ],
            report_title="Test Report",
        )

        mock_agents["planner"].run = AsyncMock(return_value=mock_plan)

        with patch("src.orchestrator.research_flow.IterativeResearchFlow") as mock_iterative:
            mock_iterative_instance = AsyncMock()
            mock_iterative_instance.run = AsyncMock(return_value="Section content")
            mock_iterative.return_value = mock_iterative_instance

            mock_agents["proofreader"].proofread = AsyncMock(
                return_value="# Final Report\n\nContent"
            )

            result = await flow.run("Test query")

            assert isinstance(result, str)
            mock_agents["proofreader"].proofread.assert_called_once()
            mock_agents["long_writer"].write_report.assert_not_called()
