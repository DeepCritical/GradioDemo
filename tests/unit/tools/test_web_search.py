"""Unit tests for WebSearchTool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock dependencies before importing to avoid import errors
import sys
sys.modules["neo4j"] = MagicMock()
sys.modules["neo4j"].GraphDatabase = MagicMock()

# Mock ddgs/duckduckgo_search
# Create a proper mock structure to avoid "ddgs.ddgs" import errors
mock_ddgs_module = MagicMock()
mock_ddgs_submodule = MagicMock()
# Create a mock DDGS class that can be instantiated
class MockDDGS:
    def __init__(self, *args, **kwargs):
        pass
    def text(self, *args, **kwargs):
        return []

mock_ddgs_submodule.DDGS = MockDDGS
mock_ddgs_module.ddgs = mock_ddgs_submodule
mock_ddgs_module.DDGS = MockDDGS
sys.modules["ddgs"] = mock_ddgs_module
sys.modules["ddgs.ddgs"] = mock_ddgs_submodule
sys.modules["duckduckgo_search"] = MagicMock()
sys.modules["duckduckgo_search"].DDGS = MockDDGS

from src.tools.web_search import WebSearchTool
from src.utils.exceptions import SearchError
from src.utils.models import Citation, Evidence


class TestWebSearchTool:
    """Tests for WebSearchTool class."""

    @pytest.fixture
    def web_search_tool(self) -> WebSearchTool:
        """Create a WebSearchTool instance."""
        return WebSearchTool()

    def test_name_property(self, web_search_tool: WebSearchTool) -> None:
        """Should return correct tool name."""
        assert web_search_tool.name == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_success(self, web_search_tool: WebSearchTool) -> None:
        """Should return evidence from successful search."""
        mock_results = [
            {
                "title": "Test Title 1",
                "body": "Test content 1",
                "href": "https://example.com/1",
            },
            {
                "title": "Test Title 2",
                "body": "Test content 2",
                "href": "https://example.com/2",
            },
        ]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert len(evidence) == 2
                assert isinstance(evidence[0], Evidence)
                assert evidence[0].citation.title == "Test Title 1"
                assert evidence[0].citation.url == "https://example.com/1"
                assert evidence[0].citation.source == "web"

    @pytest.mark.asyncio
    async def test_search_title_truncation_500_chars(self, web_search_tool: WebSearchTool) -> None:
        """Should truncate titles longer than 500 characters."""
        long_title = "A" * 600  # 600 characters
        mock_results = [
            {
                "title": long_title,
                "body": "Test content",
                "href": "https://example.com/1",
            },
        ]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert len(evidence) == 1
                truncated_title = evidence[0].citation.title
                assert len(truncated_title) == 500  # Should be exactly 500 chars
                assert truncated_title.endswith("...")  # Should end with ellipsis
                assert truncated_title.startswith("A")  # Should start with original content

    @pytest.mark.asyncio
    async def test_search_title_truncation_exactly_500_chars(self, web_search_tool: WebSearchTool) -> None:
        """Should not truncate titles that are exactly 500 characters."""
        exact_title = "A" * 500  # Exactly 500 characters
        mock_results = [
            {
                "title": exact_title,
                "body": "Test content",
                "href": "https://example.com/1",
            },
        ]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert len(evidence) == 1
                title = evidence[0].citation.title
                assert len(title) == 500
                assert title == exact_title  # Should be unchanged

    @pytest.mark.asyncio
    async def test_search_title_truncation_501_chars(self, web_search_tool: WebSearchTool) -> None:
        """Should truncate titles that are 501 characters."""
        long_title = "A" * 501  # 501 characters
        mock_results = [
            {
                "title": long_title,
                "body": "Test content",
                "href": "https://example.com/1",
            },
        ]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert len(evidence) == 1
                truncated_title = evidence[0].citation.title
                assert len(truncated_title) == 500
                assert truncated_title.endswith("...")

    @pytest.mark.asyncio
    async def test_search_missing_title(self, web_search_tool: WebSearchTool) -> None:
        """Should handle missing title gracefully."""
        mock_results = [
            {
                "body": "Test content",
                "href": "https://example.com/1",
            },
        ]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert len(evidence) == 1
                assert evidence[0].citation.title == "No Title"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, web_search_tool: WebSearchTool) -> None:
        """Should return empty list for no results."""
        with patch.object(web_search_tool._ddgs, "text", return_value=iter([])):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                evidence = await web_search_tool.search("test query", max_results=10)
                
                assert evidence == []

    @pytest.mark.asyncio
    async def test_search_raises_search_error(self, web_search_tool: WebSearchTool) -> None:
        """Should raise SearchError on exception."""
        with patch.object(web_search_tool._ddgs, "text", side_effect=Exception("API error")):
            with patch("src.tools.web_search.preprocess_query", return_value="clean query"):
                with pytest.raises(SearchError, match="DuckDuckGo search failed"):
                    await web_search_tool.search("test query", max_results=10)

    @pytest.mark.asyncio
    async def test_search_uses_preprocessed_query(self, web_search_tool: WebSearchTool) -> None:
        """Should use preprocessed query for search."""
        mock_results = [{"title": "Test", "body": "Content", "href": "https://example.com"}]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)) as mock_text:
            with patch("src.tools.web_search.preprocess_query", return_value="preprocessed query"):
                await web_search_tool.search("original query", max_results=5)
                
                # Should call text with preprocessed query
                mock_text.assert_called_once_with("preprocessed query", max_results=5)

    @pytest.mark.asyncio
    async def test_search_falls_back_to_original_query(self, web_search_tool: WebSearchTool) -> None:
        """Should fall back to original query if preprocessing returns empty."""
        mock_results = [{"title": "Test", "body": "Content", "href": "https://example.com"}]
        
        with patch.object(web_search_tool._ddgs, "text", return_value=iter(mock_results)) as mock_text:
            with patch("src.tools.web_search.preprocess_query", return_value=""):
                await web_search_tool.search("original query", max_results=5)
                
                # Should call text with original query
                mock_text.assert_called_once_with("original query", max_results=5)

