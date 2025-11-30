"""Unit tests for WebSearchTool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.web_search import WebSearchTool
from src.utils.models import Citation, Evidence


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    @pytest.mark.asyncio
    async def test_search_returns_evidence(self, mocker):
        """WebSearchTool should return Evidence objects from Tavily search."""
        # Mock Tavily response
        mock_tavily_response = {
            "results": [
                {
                    "title": "AI Research Breakthrough",
                    "url": "https://example.com/ai-research",
                    "content": "New advances in artificial intelligence...",
                    "score": 0.95,
                },
                {
                    "title": "Machine Learning Tutorial",
                    "url": "https://example.com/ml-tutorial",
                    "content": "Learn machine learning basics...",
                    "score": 0.87,
                },
            ]
        }

        # Mock TavilyClient
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)

        # Mock settings
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        # Act
        tool = WebSearchTool()
        results = await tool.search("AI research", max_results=10)

        # Assert
        assert len(results) == 2
        assert isinstance(results[0], Evidence)
        assert results[0].citation.source == "web"
        assert results[0].citation.title == "AI Research Breakthrough"
        assert results[0].citation.url == "https://example.com/ai-research"
        assert "artificial intelligence" in results[0].content
        assert results[0].relevance == 0.95

        assert results[1].citation.title == "Machine Learning Tutorial"
        assert results[1].relevance == 0.87

        # Verify TavilyClient was called correctly
        mock_client.search.assert_called_once_with(query="AI research", max_results=10)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mocker):
        """WebSearchTool should return empty list when no results."""
        mock_tavily_response = {"results": []}

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        results = await tool.search("nonexistent query xyz123")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_missing_fields(self, mocker):
        """WebSearchTool should handle missing optional fields in Tavily response."""
        # Response with missing optional fields (but has required content)
        mock_tavily_response = {
            "results": [
                {
                    "url": "https://example.com/page",
                    "content": "Some content here",
                    # Missing: title, score
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        results = await tool.search("test query")

        assert len(results) == 1
        assert results[0].citation.title == "No Title"
        assert results[0].content == "Some content here"
        assert results[0].relevance == 0.0

    @pytest.mark.asyncio
    async def test_search_handles_exception(self, mocker):
        """WebSearchTool should return empty list on exception."""
        mock_client = MagicMock()
        mock_client.search = MagicMock(side_effect=Exception("API Error"))
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        results = await tool.search("test query")

        # Should catch exception and return empty list
        assert results == []

    @pytest.mark.asyncio
    async def test_search_max_results_parameter(self, mocker):
        """WebSearchTool should respect max_results parameter."""
        mock_tavily_response = {"results": []}

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        await tool.search("test query", max_results=25)

        # Verify max_results is passed to Tavily
        mock_client.search.assert_called_once_with(query="test query", max_results=25)

    def test_name_property(self):
        """WebSearchTool should have name property returning 'web'."""
        with patch("src.tools.web_search.settings.tavily_api_key", "test-api-key"):
            tool = WebSearchTool()
            assert tool.name == "web"

    def test_init_with_api_key(self, mocker):
        """WebSearchTool should initialize with API key from settings."""
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "my-tavily-key")
        
        tool = WebSearchTool()
        
        assert tool.api_key == "my-tavily-key"

    def test_init_without_api_key(self, mocker):
        """WebSearchTool should warn when initialized without API key."""
        mocker.patch("src.tools.web_search.settings.tavily_api_key", None)
        
        # Should not raise, but will log warning
        tool = WebSearchTool()
        
        assert tool.api_key is None

    @pytest.mark.asyncio
    async def test_search_runs_in_executor(self, mocker):
        """WebSearchTool should run blocking Tavily call in executor."""
        mock_tavily_response = {"results": []}

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        # Mock the event loop's run_in_executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(return_value=mock_tavily_response)
            mock_get_loop.return_value = mock_loop

            tool = WebSearchTool()
            await tool.search("test query")

            # Verify run_in_executor was called
            assert mock_loop.run_in_executor.called

    @pytest.mark.asyncio
    async def test_search_preserves_citation_metadata(self, mocker):
        """WebSearchTool should preserve all citation metadata from Tavily."""
        mock_tavily_response = {
            "results": [
                {
                    "title": "Complete Article",
                    "url": "https://example.com/complete",
                    "content": "Full content here",
                    "score": 0.99,
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        results = await tool.search("test query")

        citation = results[0].citation
        assert citation.title == "Complete Article"
        assert citation.url == "https://example.com/complete"
        assert citation.source == "web"
        assert citation.date == "Unknown"
        assert citation.authors == []

    @pytest.mark.asyncio
    async def test_search_default_max_results(self, mocker):
        """WebSearchTool should use default max_results=10 when not specified."""
        mock_tavily_response = {"results": []}

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        await tool.search("test query")

        # Verify default max_results=10 is used
        mock_client.search.assert_called_once_with(query="test query", max_results=10)

    @pytest.mark.asyncio
    async def test_search_multiple_results_with_scores(self, mocker):
        """WebSearchTool should handle multiple results with varying relevance scores."""
        mock_tavily_response = {
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1", "score": 1.0},
                {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2", "score": 0.8},
                {"title": "Result 3", "url": "https://example.com/3", "content": "Content 3", "score": 0.6},
                {"title": "Result 4", "url": "https://example.com/4", "content": "Content 4", "score": 0.4},
            ]
        }

        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=mock_tavily_response)
        
        mocker.patch("src.tools.web_search.TavilyClient", return_value=mock_client)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "test-api-key")

        tool = WebSearchTool()
        results = await tool.search("test query")

        assert len(results) == 4
        assert results[0].relevance == 1.0
        assert results[1].relevance == 0.8
        assert results[2].relevance == 0.6
        assert results[3].relevance == 0.4

    @pytest.mark.asyncio
    async def test_search_tavily_client_initialization(self, mocker):
        """WebSearchTool should initialize TavilyClient with correct API key."""
        mock_tavily_response = {"results": []}

        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.search = MagicMock(return_value=mock_tavily_response)
        mock_client_class.return_value = mock_client_instance
        
        mocker.patch("src.tools.web_search.TavilyClient", mock_client_class)
        mocker.patch("src.tools.web_search.settings.tavily_api_key", "my-secret-key")

        tool = WebSearchTool()
        await tool.search("test query")

        # Verify TavilyClient was initialized with the API key
        mock_client_class.assert_called_once_with(api_key="my-secret-key")
