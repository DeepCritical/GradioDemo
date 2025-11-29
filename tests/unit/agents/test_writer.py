"""Unit tests for WriterAgent."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult

from src.agents.writer import WriterAgent, create_writer_agent
from src.utils.exceptions import ConfigurationError


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
    result.output = "# Research Report\n\nThis is a test report with citations [1].\n\nReferences:\n[1] https://example.com"
    return result


@pytest.fixture
def writer_agent(mock_model: MagicMock) -> WriterAgent:
    """Create a WriterAgent instance with mocked model."""
    return WriterAgent(model=mock_model)


class TestWriterAgentInit:
    """Test WriterAgent initialization."""

    def test_writer_agent_init_with_model(self, mock_model: MagicMock) -> None:
        """Test WriterAgent initialization with provided model."""
        agent = WriterAgent(model=mock_model)
        assert agent.model == mock_model
        assert agent.agent is not None

    @patch("src.agents.writer.get_model")
    def test_writer_agent_init_without_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test WriterAgent initialization without model (uses default)."""
        mock_get_model.return_value = mock_model
        agent = WriterAgent()
        assert agent.model == mock_model
        mock_get_model.assert_called_once()

    def test_writer_agent_has_correct_system_prompt(self, writer_agent: WriterAgent) -> None:
        """Test that WriterAgent has correct system prompt."""
        # System prompt should exist and contain key instructions
        # Check the source constant directly since system_prompt property may be a callable
        from src.agents.writer import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert "researcher" in SYSTEM_PROMPT.lower()
        assert "markdown" in SYSTEM_PROMPT.lower()


class TestWriteReport:
    """Test write_report() method."""

    @pytest.mark.asyncio
    async def test_write_report_basic(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test basic report writing."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "What is the capital of France?"
        findings = "Paris is the capital of France [1].\n\n[1] https://example.com"

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert "Research Report" in result
        assert writer_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_write_report_with_output_length(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing with output length specification."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = "Test findings"
        output_length = "500 words"

        result = await writer_agent.write_report(
            query=query, findings=findings, output_length=output_length
        )

        assert isinstance(result, str)
        # Check that output_length was included in the prompt
        call_args = writer_agent.agent.run.call_args[0][0]
        assert "500 words" in call_args

    @pytest.mark.asyncio
    async def test_write_report_with_instructions(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing with additional instructions."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = "Test findings"
        output_instructions = "Use formal language"

        result = await writer_agent.write_report(
            query=query, findings=findings, output_instructions=output_instructions
        )

        assert isinstance(result, str)
        # Check that instructions were included in the prompt
        call_args = writer_agent.agent.run.call_args[0][0]
        assert "formal language" in call_args

    @pytest.mark.asyncio
    async def test_write_report_with_citations(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing includes citations."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = "Test findings with citation [1].\n\n[1] https://example.com"

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert "[1]" in result or "example.com" in result

    @pytest.mark.asyncio
    async def test_write_report_empty_findings(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing with empty findings."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = ""

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert writer_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_write_report_very_long_findings(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing with very long findings."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = "Test findings. " * 1000  # Very long findings

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert writer_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_write_report_special_characters(
        self, writer_agent: WriterAgent, mock_agent_result: AgentRunResult[Any]
    ) -> None:
        """Test report writing with special characters in findings."""
        writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        query = "Test query"
        findings = "Findings with special chars: <>&\"'"

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert writer_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_write_report_llm_failure(self, writer_agent: WriterAgent) -> None:
        """Test report writing handles LLM failures gracefully."""
        writer_agent.agent.run = AsyncMock(side_effect=Exception("LLM error"))

        query = "Test query"
        findings = "Test findings"

        result = await writer_agent.write_report(query=query, findings=findings)

        # Should return fallback report
        assert isinstance(result, str)
        assert "Research Report" in result
        assert "fallback" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_write_report_returns_fallback_on_error(self, writer_agent: WriterAgent) -> None:
        """Test that fallback report is returned on error."""
        writer_agent.agent.run = AsyncMock(side_effect=RuntimeError("Test error"))

        query = "Test query"
        findings = "Test findings"

        result = await writer_agent.write_report(query=query, findings=findings)

        assert isinstance(result, str)
        assert query in result
        assert findings in result


class TestCreateWriterAgent:
    """Test create_writer_agent factory function."""

    @patch("src.agents.writer.get_model")
    @patch("src.agents.writer.WriterAgent")
    def test_create_writer_agent_success(
        self,
        mock_writer_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test successful writer agent creation."""
        mock_get_model.return_value = mock_model
        mock_agent_instance = MagicMock()
        mock_writer_agent_class.return_value = mock_agent_instance

        result = create_writer_agent()

        assert result == mock_agent_instance
        mock_writer_agent_class.assert_called_once_with(model=mock_model)

    @patch("src.agents.writer.get_model")
    @patch("src.agents.writer.WriterAgent")
    def test_create_writer_agent_with_custom_model(
        self,
        mock_writer_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test writer agent creation with custom model."""
        mock_agent_instance = MagicMock()
        mock_writer_agent_class.return_value = mock_agent_instance

        result = create_writer_agent(model=mock_model)

        assert result == mock_agent_instance
        mock_writer_agent_class.assert_called_once_with(model=mock_model)
        mock_get_model.assert_not_called()

    @patch("src.agents.writer.get_model")
    @patch("src.agents.writer.WriterAgent")
    def test_create_writer_agent_handles_errors(
        self,
        mock_writer_agent_class: MagicMock,
        mock_get_model: MagicMock,
    ) -> None:
        """Test writer agent creation handles errors."""
        mock_get_model.side_effect = Exception("Model error")
        mock_writer_agent_class.side_effect = Exception("Agent creation error")

        with pytest.raises(ConfigurationError) as exc_info:
            create_writer_agent()

        assert "Failed to create writer agent" in str(exc_info.value)
