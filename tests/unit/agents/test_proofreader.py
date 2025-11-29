"""Unit tests for ProofreaderAgent."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult

from src.agents.proofreader import ProofreaderAgent, create_proofreader_agent
from src.utils.models import ReportDraft, ReportDraftSection


@pytest.fixture
def mock_model() -> MagicMock:
    """Create a mock Pydantic AI model."""
    model = MagicMock()
    model.name = "test-model"
    return model


@pytest.fixture
def mock_agent_result() -> AgentRunResult[Any]:
    """Create a mock agent result."""
    result = MagicMock(spec=AgentRunResult)
    result.output = """# Final Report

## Summary
This is a polished report.

## Introduction
Introduction content.

## References:
[1] https://example.com
"""
    return result


@pytest.fixture
def proofreader_agent(mock_model: MagicMock) -> ProofreaderAgent:
    """Create a ProofreaderAgent instance with mocked model."""
    return ProofreaderAgent(model=mock_model)


@pytest.fixture
def sample_report_draft() -> ReportDraft:
    """Create a sample ReportDraft for testing."""
    return ReportDraft(
        sections=[
            ReportDraftSection(
                section_title="Introduction",
                section_content="Introduction content with [1].",
            ),
            ReportDraftSection(
                section_title="Methods",
                section_content="Methods content with [2].",
            ),
        ]
    )


class TestProofreaderAgentInit:
    """Test ProofreaderAgent initialization."""

    def test_proofreader_agent_init_with_model(self, mock_model: MagicMock) -> None:
        """Test ProofreaderAgent initialization with provided model."""
        agent = ProofreaderAgent(model=mock_model)
        assert agent.model == mock_model
        assert agent.agent is not None

    @patch("src.agents.proofreader.get_model")
    def test_proofreader_agent_init_without_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test ProofreaderAgent initialization without model (uses default)."""
        mock_get_model.return_value = mock_model
        agent = ProofreaderAgent()
        assert agent.model == mock_model
        mock_get_model.assert_called_once()

    def test_proofreader_agent_has_correct_system_prompt(
        self, proofreader_agent: ProofreaderAgent
    ) -> None:
        """Test that ProofreaderAgent has correct system prompt."""
        # System prompt should exist and contain key instructions
        # Check the source constant directly since system_prompt property may be a callable
        from src.agents.proofreader import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert "proofread" in SYSTEM_PROMPT.lower()
        assert "report" in SYSTEM_PROMPT.lower()


class TestProofread:
    """Test proofread() method."""

    @pytest.mark.asyncio
    async def test_proofread_basic(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test basic proofreading."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        result = await proofreader_agent.proofread(query=query, report_draft=sample_report_draft)

        assert isinstance(result, str)
        assert "Final Report" in result or "Introduction" in result
        assert proofreader_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_proofread_single_section(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test proofreading with single section."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="Single Section",
                    section_content="Content",
                )
            ]
        )

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)
        assert proofreader_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_proofread_multiple_sections(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test proofreading with multiple sections."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await proofreader_agent.proofread(query="Test", report_draft=sample_report_draft)

        assert isinstance(result, str)
        # Check that draft was included in prompt
        call_args = proofreader_agent.agent.run.call_args[0][0]
        assert "Introduction" in call_args or "Methods" in call_args

    @pytest.mark.asyncio
    async def test_proofread_removes_duplicates(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test that proofreader removes duplicate content."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="Section 1",
                    section_content="Duplicate content",
                ),
                ReportDraftSection(
                    section_title="Section 2",
                    section_content="Duplicate content",  # Duplicate
                ),
            ]
        )

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)
        # System prompt should instruct to remove duplicates
        call_args = proofreader_agent.agent.run.call_args[0][0]
        assert "duplicate" in call_args.lower() or "De-duplicate" in call_args

    @pytest.mark.asyncio
    async def test_proofread_adds_summary(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test that proofreader adds summary."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await proofreader_agent.proofread(query="Test", report_draft=sample_report_draft)

        assert isinstance(result, str)
        # System prompt should instruct to add summary - check source constant
        from src.agents.proofreader import SYSTEM_PROMPT

        assert "summary" in SYSTEM_PROMPT.lower() or "Add a summary" in SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_proofread_preserves_references(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test that proofreader preserves references."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await proofreader_agent.proofread(query="Test", report_draft=sample_report_draft)

        assert isinstance(result, str)
        # System prompt should instruct to preserve sources - check source constant
        from src.agents.proofreader import SYSTEM_PROMPT

        assert (
            "sources" in SYSTEM_PROMPT.lower()
            or "references" in SYSTEM_PROMPT.lower()
            or "Preserve sources" in SYSTEM_PROMPT
        )

    @pytest.mark.asyncio
    async def test_proofread_empty_draft(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test proofreading with empty draft."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(sections=[])

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)
        # When draft is empty, agent returns early without calling run
        assert "Research Report" in result
        assert "Query" in result
        # Agent.run should not be called for empty drafts (early return)
        assert not proofreader_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_proofread_single_section_draft(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test proofreading with single section draft."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="Single Section",
                    section_content="Content",
                )
            ]
        )

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_proofread_very_long_draft(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test proofreading with very long draft."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="Long Section",
                    section_content="Content. " * 1000,  # Very long
                )
            ]
        )

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)
        assert proofreader_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_proofread_malformed_sections(
        self,
        proofreader_agent: ProofreaderAgent,
        mock_agent_result: AgentRunResult[Any],
    ) -> None:
        """Test proofreading with malformed sections."""
        proofreader_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="",
                    section_content="",  # Empty section
                )
            ]
        )

        result = await proofreader_agent.proofread(query="Test", report_draft=report_draft)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_proofread_llm_failure(
        self, proofreader_agent: ProofreaderAgent, sample_report_draft: ReportDraft
    ) -> None:
        """Test proofreading handles LLM failures gracefully."""
        proofreader_agent.agent.run = AsyncMock(side_effect=Exception("LLM error"))

        result = await proofreader_agent.proofread(query="Test", report_draft=sample_report_draft)

        # Should return fallback report
        assert isinstance(result, str)
        assert "Research Report" in result
        assert "Introduction" in result

    @pytest.mark.asyncio
    async def test_proofread_returns_fallback_on_error(
        self, proofreader_agent: ProofreaderAgent, sample_report_draft: ReportDraft
    ) -> None:
        """Test that fallback report is returned on error."""
        proofreader_agent.agent.run = AsyncMock(side_effect=RuntimeError("Test error"))

        result = await proofreader_agent.proofread(query="Test", report_draft=sample_report_draft)

        assert isinstance(result, str)
        # Fallback should combine sections manually
        assert sample_report_draft.sections[0].section_title in result


class TestCreateProofreaderAgent:
    """Test create_proofreader_agent factory function."""

    @patch("src.agents.proofreader.get_model")
    @patch("src.agents.proofreader.ProofreaderAgent")
    def test_create_proofreader_agent_success(
        self,
        mock_proofreader_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test successful proofreader agent creation."""
        mock_get_model.return_value = mock_model
        mock_agent_instance = MagicMock()
        mock_proofreader_agent_class.return_value = mock_agent_instance

        result = create_proofreader_agent()

        assert result == mock_agent_instance
        mock_proofreader_agent_class.assert_called_once_with(model=mock_model)

    @patch("src.agents.proofreader.get_model")
    @patch("src.agents.proofreader.ProofreaderAgent")
    def test_create_proofreader_agent_with_custom_model(
        self,
        mock_proofreader_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test proofreader agent creation with custom model."""
        mock_agent_instance = MagicMock()
        mock_proofreader_agent_class.return_value = mock_agent_instance

        result = create_proofreader_agent(model=mock_model)

        assert result == mock_agent_instance
        mock_proofreader_agent_class.assert_called_once_with(model=mock_model)
        mock_get_model.assert_not_called()
