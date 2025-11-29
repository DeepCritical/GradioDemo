"""Unit tests for SearchHandler."""

from unittest.mock import AsyncMock

import pytest

from src.tools.search_handler import SearchHandler
from src.utils.exceptions import SearchError
from src.utils.models import Citation, Evidence


class TestSearchHandler:
    """Tests for SearchHandler."""

    @pytest.mark.asyncio
    async def test_execute_aggregates_results(self):
        """SearchHandler should aggregate results from all tools."""
        # Create mock tools
        mock_tool_1 = AsyncMock()
        mock_tool_1.name = "pubmed"
        mock_tool_1.search = AsyncMock(
            return_value=[
                Evidence(
                    content="Result 1",
                    citation=Citation(source="pubmed", title="T1", url="u1", date="2024"),
                )
            ]
        )

        mock_tool_2 = AsyncMock()
        mock_tool_2.name = "pubmed"  # Type system currently restricts to pubmed
        mock_tool_2.search = AsyncMock(return_value=[])

        handler = SearchHandler(tools=[mock_tool_1, mock_tool_2])
        result = await handler.execute("test query")

        assert result.total_found == 1
        assert "pubmed" in result.sources_searched
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_handles_tool_failure(self):
        """SearchHandler should continue if one tool fails."""
        mock_tool_ok = AsyncMock()
        mock_tool_ok.name = "pubmed"
        mock_tool_ok.search = AsyncMock(
            return_value=[
                Evidence(
                    content="Good result",
                    citation=Citation(source="pubmed", title="T", url="u", date="2024"),
                )
            ]
        )

        mock_tool_fail = AsyncMock()
        mock_tool_fail.name = "pubmed"  # Mocking a second pubmed instance failing
        mock_tool_fail.search = AsyncMock(side_effect=SearchError("API down"))

        handler = SearchHandler(tools=[mock_tool_ok, mock_tool_fail])
        result = await handler.execute("test")

        assert result.total_found == 1
        assert "pubmed" in result.sources_searched
        assert len(result.errors) == 1
        # The error message format is "{tool.name}: {error!s}"
        assert "pubmed: API down" in result.errors[0]

    @pytest.mark.asyncio
    async def test_search_handler_pubmed_only(self):
        """SearchHandler should work with only PubMed tool."""
        # This is the specific test requested in Phase 9 spec
        from src.tools.pubmed import PubMedTool

        mock_pubmed = AsyncMock(spec=PubMedTool)
        mock_pubmed.name = "pubmed"
        mock_pubmed.search.return_value = []

        handler = SearchHandler(tools=[mock_pubmed], timeout=30.0)
        result = await handler.execute("metformin diabetes", max_results_per_tool=3)

        assert result.sources_searched == ["pubmed"]
        assert "web" not in result.sources_searched
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_search_timeout(self):
        """SearchHandler should raise SearchError when tool times out."""
        import asyncio

        mock_tool = AsyncMock()
        mock_tool.name = "pubmed"

        # Make search sleep longer than timeout
        async def slow_search(query: str, max_results: int) -> list[Evidence]:
            await asyncio.sleep(1.0)  # Longer than 0.1s timeout
            return []

        mock_tool.search = slow_search

        handler = SearchHandler(tools=[mock_tool], timeout=0.1)
        result = await handler.execute("test query")

        # Should have error for timed out tool
        assert len(result.errors) == 1
        assert "timed out" in result.errors[0].lower()
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_execute_with_multiple_different_tools(self):
        """SearchHandler should execute multiple different tools in parallel."""
        from src.tools.europepmc import EuropePMCTool
        from src.tools.pubmed import PubMedTool

        mock_pubmed = AsyncMock(spec=PubMedTool)
        mock_pubmed.name = "pubmed"
        mock_pubmed.search = AsyncMock(
            return_value=[
                Evidence(
                    content="PubMed result",
                    citation=Citation(source="pubmed", title="T1", url="u1", date="2024"),
                )
            ]
        )

        mock_europepmc = AsyncMock(spec=EuropePMCTool)
        mock_europepmc.name = "europepmc"
        mock_europepmc.search = AsyncMock(
            return_value=[
                Evidence(
                    content="Europe PMC result",
                    citation=Citation(source="europepmc", title="T2", url="u2", date="2024"),
                )
            ]
        )

        handler = SearchHandler(tools=[mock_pubmed, mock_europepmc])
        result = await handler.execute("test query")

        assert result.total_found == 2
        assert "pubmed" in result.sources_searched
        assert "europepmc" in result.sources_searched
        assert len(result.errors) == 0

        # Verify both tools were called
        mock_pubmed.search.assert_called_once()
        mock_europepmc.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_empty_tools_list(self):
        """SearchHandler should handle empty tools list gracefully."""
        handler = SearchHandler(tools=[])
        result = await handler.execute("test query")

        assert result.total_found == 0
        assert result.sources_searched == []
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_with_all_tools_failing(self):
        """SearchHandler should return errors when all tools fail."""
        mock_tool_1 = AsyncMock()
        mock_tool_1.name = "pubmed"
        mock_tool_1.search = AsyncMock(side_effect=SearchError("Tool 1 failed"))

        mock_tool_2 = AsyncMock()
        mock_tool_2.name = "europepmc"
        mock_tool_2.search = AsyncMock(side_effect=SearchError("Tool 2 failed"))

        handler = SearchHandler(tools=[mock_tool_1, mock_tool_2])
        result = await handler.execute("test query")

        assert result.total_found == 0
        assert len(result.errors) == 2
        assert "pubmed" in result.errors[0].lower()
        assert "europepmc" in result.errors[1].lower()
        assert result.sources_searched == []

    @pytest.mark.asyncio
    async def test_execute_preserves_tool_order(self):
        """SearchHandler should preserve tool order in sources_searched."""
        mock_tool_1 = AsyncMock()
        mock_tool_1.name = "pubmed"
        mock_tool_1.search = AsyncMock(return_value=[])

        mock_tool_2 = AsyncMock()
        mock_tool_2.name = "europepmc"
        mock_tool_2.search = AsyncMock(return_value=[])

        mock_tool_3 = AsyncMock()
        mock_tool_3.name = "clinicaltrials"
        mock_tool_3.search = AsyncMock(return_value=[])

        handler = SearchHandler(tools=[mock_tool_1, mock_tool_2, mock_tool_3])
        result = await handler.execute("test query")

        # Should preserve order
        assert result.sources_searched == ["pubmed", "europepmc", "clinicaltrials"]
