"""Unit tests for tool executor with RAGAgent support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.tool_executor import (
    _evidence_to_text,
    _get_rag_tool,
    execute_agent_task,
    execute_tool_tasks,
)
from src.utils.exceptions import ConfigurationError
from src.utils.models import AgentTask, Citation, Evidence, ToolAgentOutput


class TestEvidenceToText:
    """Tests for _evidence_to_text helper function."""

    def test_evidence_to_text_formats_correctly(self):
        """_evidence_to_text should format Evidence objects with citations."""
        evidence_list = [
            Evidence(
                content="First piece of evidence",
                citation=Citation(
                    source="rag",
                    title="First Title",
                    url="https://example.com/1",
                    date="2024-01-15",
                    authors=["Author A"],
                ),
                relevance=0.9,
            ),
            Evidence(
                content="Second piece of evidence",
                citation=Citation(
                    source="rag",
                    title="Second Title",
                    url="https://example.com/2",
                    date="2024-01-16",
                    authors=["Author B", "Author C"],
                ),
                relevance=0.8,
            ),
        ]

        result = _evidence_to_text(evidence_list)

        assert "[1]" in result
        assert "First Title" in result
        assert "https://example.com/1" in result
        assert "First piece of evidence" in result
        assert "[2]" in result
        assert "Second Title" in result
        assert "https://example.com/2" in result
        assert "Second piece of evidence" in result
        assert "---" in result  # Separator

    def test_evidence_to_text_empty_list(self):
        """_evidence_to_text should handle empty list."""
        result = _evidence_to_text([])
        assert result == "No evidence found."


class TestGetRAGTool:
    """Tests for _get_rag_tool helper function."""

    @patch("src.tools.tool_executor.create_rag_tool")
    def test_get_rag_tool_creates_tool(self, mock_create):
        """_get_rag_tool should create RAG tool on first call."""
        mock_tool = MagicMock()
        mock_create.return_value = mock_tool

        # Reset global state
        import src.tools.tool_executor as module

        module._rag_tool = None

        result = _get_rag_tool()

        assert result == mock_tool
        mock_create.assert_called_once()

    @patch("src.tools.tool_executor.create_rag_tool")
    def test_get_rag_tool_returns_cached(self, mock_create):
        """_get_rag_tool should return cached tool on subsequent calls."""
        mock_tool = MagicMock()
        mock_create.return_value = mock_tool

        # Reset global state
        import src.tools.tool_executor as module

        module._rag_tool = None

        # First call
        result1 = _get_rag_tool()
        # Second call
        result2 = _get_rag_tool()

        assert result1 == result2
        assert mock_create.call_count == 1  # Only called once

    @patch("src.tools.tool_executor.create_rag_tool")
    def test_get_rag_tool_handles_configuration_error(self, mock_create):
        """_get_rag_tool should return None if RAG unavailable."""
        mock_create.side_effect = ConfigurationError("OPENAI_API_KEY required")

        # Reset global state
        import src.tools.tool_executor as module

        module._rag_tool = None

        result = _get_rag_tool()

        assert result is None


class TestExecuteAgentTaskRAGAgent:
    """Tests for execute_agent_task with RAGAgent."""

    @pytest.mark.asyncio
    async def test_execute_rag_agent_success(self):
        """execute_agent_task should execute RAGAgent and return ToolAgentOutput."""
        # Mock RAG tool
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(
            return_value=[
                Evidence(
                    content="Test evidence content",
                    citation=Citation(
                        source="rag",
                        title="Test Title",
                        url="https://example.com/test",
                        date="2024",
                        authors=["Author"],
                    ),
                    relevance=0.9,
                )
            ]
        )

        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            task = AgentTask(
                agent="RAGAgent",
                query="test query",
                gap="test gap",
            )

            result = await execute_agent_task(task)

            assert isinstance(result, ToolAgentOutput)
            assert "Test evidence content" in result.output
            assert "Test Title" in result.output
            assert "https://example.com/test" in result.sources
            mock_rag_tool.search.assert_called_once_with("test query", max_results=10)

    @pytest.mark.asyncio
    async def test_execute_rag_agent_empty_results(self):
        """execute_agent_task should handle empty RAG results."""
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(return_value=[])

        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            task = AgentTask(agent="RAGAgent", query="test", gap="gap")

            result = await execute_agent_task(task)

            assert isinstance(result, ToolAgentOutput)
            assert "No relevant evidence found" in result.output
            assert result.sources == []

    @pytest.mark.asyncio
    async def test_execute_rag_agent_unavailable(self):
        """execute_agent_task should handle RAG service unavailable."""
        with patch("src.tools.tool_executor._get_rag_tool", return_value=None):
            task = AgentTask(agent="RAGAgent", query="test", gap="gap")

            result = await execute_agent_task(task)

            assert isinstance(result, ToolAgentOutput)
            assert "RAG service unavailable" in result.output
            assert "OPENAI_API_KEY required" in result.output
            assert result.sources == []

    @pytest.mark.asyncio
    async def test_execute_rag_agent_extracts_urls(self):
        """execute_agent_task should extract URLs from evidence citations."""
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(
            return_value=[
                Evidence(
                    content="Content 1",
                    citation=Citation(
                        source="rag",
                        title="Title 1",
                        url="https://example.com/1",
                        date="2024",
                        authors=[],
                    ),
                ),
                Evidence(
                    content="Content 2",
                    citation=Citation(
                        source="rag",
                        title="Title 2",
                        url="https://example.com/2",
                        date="2024",
                        authors=[],
                    ),
                ),
                Evidence(
                    content="Content 3",
                    citation=Citation(
                        source="rag",
                        title="Title 3",
                        url="",  # No URL
                        date="2024",
                        authors=[],
                    ),
                ),
            ]
        )

        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            task = AgentTask(agent="RAGAgent", query="test", gap="gap")

            result = await execute_agent_task(task)

            assert "https://example.com/1" in result.sources
            assert "https://example.com/2" in result.sources
            assert len(result.sources) == 2  # Only URLs with values

    @pytest.mark.asyncio
    async def test_execute_rag_agent_handles_error(self):
        """execute_agent_task should handle RAG search errors gracefully."""
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(side_effect=Exception("RAG error"))

        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            task = AgentTask(agent="RAGAgent", query="test", gap="gap")

            result = await execute_agent_task(task)

            assert isinstance(result, ToolAgentOutput)
            assert "Error executing" in result.output
            assert "RAGAgent" in result.output


class TestExecuteToolTasksRAGAgent:
    """Tests for execute_tool_tasks with RAGAgent tasks."""

    @pytest.mark.asyncio
    async def test_execute_tool_tasks_with_rag_agent(self):
        """execute_tool_tasks should handle RAGAgent tasks."""
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(
            return_value=[
                Evidence(
                    content="RAG result",
                    citation=Citation(
                        source="rag",
                        title="RAG Title",
                        url="https://rag.example.com",
                        date="2024",
                        authors=[],
                    ),
                )
            ]
        )

        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            tasks = [
                AgentTask(agent="RAGAgent", query="test query", gap="gap1"),
            ]

            results = await execute_tool_tasks(tasks)

            assert len(results) == 1
            assert "RAGAgent" in next(iter(results.keys()))
            assert "RAG result" in next(iter(results.values())).output

    @pytest.mark.asyncio
    async def test_execute_tool_tasks_mixed_agents(self):
        """execute_tool_tasks should handle mixed agent types."""
        # Mock RAG tool
        mock_rag_tool = MagicMock()
        mock_rag_tool.search = AsyncMock(
            return_value=[
                Evidence(
                    content="RAG content",
                    citation=Citation(
                        source="rag",
                        title="RAG",
                        url="https://rag.com",
                        date="2024",
                        authors=[],
                    ),
                )
            ]
        )

        # Mock web search
        with patch("src.tools.tool_executor._get_rag_tool", return_value=mock_rag_tool):
            with patch("src.tools.tool_executor.web_search", new_callable=AsyncMock) as mock_web:
                mock_web.return_value = "Web search result"

                tasks = [
                    AgentTask(agent="RAGAgent", query="rag query", gap="gap1"),
                    AgentTask(agent="WebSearchAgent", query="web query", gap="gap2"),
                ]

                results = await execute_tool_tasks(tasks)

                assert len(results) == 2
                # Check RAG result
                rag_key = next(k for k in results.keys() if "RAGAgent" in k)
                assert "RAG content" in results[rag_key].output
                # Check web search result
                web_key = next(k for k in results.keys() if "WebSearchAgent" in k)
                assert "Web search result" in results[web_key].output
