"""Unit tests for PlannerAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.planner_agent import PlannerAgent, create_planner_agent
from src.utils.models import ReportPlan, ReportPlanSection


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock Pydantic AI model."""
        return MagicMock()

    @pytest.fixture
    def mock_agent_run_result(self):
        """Create a mock agent run result."""
        mock_result = MagicMock()
        mock_result.output = ReportPlan(
            background_context="Python is a programming language.",
            report_outline=[
                ReportPlanSection(
                    title="Introduction",
                    key_question="What is Python?",
                ),
                ReportPlanSection(
                    title="Features",
                    key_question="What are Python's main features?",
                ),
            ],
            report_title="Python Programming Language Overview",
        )
        return mock_result

    @pytest.mark.asyncio
    async def test_planner_agent_creates_report_plan(self, mock_model, mock_agent_run_result):
        """PlannerAgent should create a valid ReportPlan."""
        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_agent_run_result)

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = mock_agent

                planner = PlannerAgent(model=mock_model)
                planner.agent = mock_agent

                result = await planner.run("What is Python?")

                assert isinstance(result, ReportPlan)
                assert result.report_title == "Python Programming Language Overview"
                assert len(result.report_outline) == 2
                assert result.report_outline[0].title == "Introduction"
                assert result.report_outline[0].key_question == "What is Python?"

    @pytest.mark.asyncio
    async def test_planner_agent_handles_empty_outline(self, mock_model):
        """PlannerAgent should return fallback plan when outline is empty."""
        mock_result = MagicMock()
        mock_result.output = ReportPlan(
            background_context="Some context",
            report_outline=[],  # Empty outline
            report_title="Test Report",
        )

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = mock_agent

                planner = PlannerAgent(model=mock_model)
                planner.agent = mock_agent

                result = await planner.run("Test query")

                # Should return fallback plan
                assert isinstance(result, ReportPlan)
                assert len(result.report_outline) > 0
                assert "Overview" in result.report_outline[0].title

    @pytest.mark.asyncio
    async def test_planner_agent_handles_llm_failure(self, mock_model):
        """PlannerAgent should return fallback plan on LLM failure."""
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=Exception("API Error"))

        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = mock_agent

                planner = PlannerAgent(model=mock_model)
                planner.agent = mock_agent

                result = await planner.run("Test query")

                # Should return fallback plan
                assert isinstance(result, ReportPlan)
                assert len(result.report_outline) > 0
                # Fallback plan has title "Research Findings" and empty background_context
                assert result.report_outline[0].title == "Research Findings"
                assert result.background_context == ""

    @pytest.mark.asyncio
    async def test_planner_agent_uses_tools(self, mock_model, mock_agent_run_result):
        """PlannerAgent should use web_search and crawl_website tools."""
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_run_result)

        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = mock_agent

                planner = PlannerAgent(model=mock_model)
                planner.agent = mock_agent

                await planner.run("What is Python?")

                # Verify agent was initialized with tools
                mock_agent_class.assert_called_once()
                call_kwargs = mock_agent_class.call_args[1]
                assert "tools" in call_kwargs
                assert len(call_kwargs["tools"]) == 2  # web_search and crawl_website

    @pytest.mark.asyncio
    async def test_create_planner_agent_factory(self, mock_model):
        """create_planner_agent should create a PlannerAgent instance."""
        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = AsyncMock()

                planner = create_planner_agent(model=mock_model)

                assert isinstance(planner, PlannerAgent)
                assert planner.model == mock_model

    @pytest.mark.asyncio
    async def test_create_planner_agent_uses_default_model(self):
        """create_planner_agent should use default model when None provided."""
        mock_model = MagicMock()

        with patch("src.orchestrator.planner_agent.get_model") as mock_get_model:
            mock_get_model.return_value = mock_model

            with patch("src.orchestrator.planner_agent.Agent") as mock_agent_class:
                mock_agent_class.return_value = AsyncMock()

                planner = create_planner_agent()

                assert isinstance(planner, PlannerAgent)
                mock_get_model.assert_called_once()
