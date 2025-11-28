"""Unit tests for RAGTool."""

from unittest.mock import MagicMock, patch

import pytest

from src.tools.rag_tool import RAGTool, create_rag_tool
from src.utils.exceptions import ConfigurationError
from src.utils.models import Evidence


class TestRAGTool:
    """Tests for RAGTool class."""

    def test_name_property(self):
        """RAGTool should have name 'rag'."""
        tool = RAGTool(rag_service=None)
        assert tool.name == "rag"

    def test_init_with_rag_service(self):
        """RAGTool should accept provided RAG service."""
        mock_service = MagicMock()
        tool = RAGTool(rag_service=mock_service)
        assert tool._rag_service == mock_service

    def test_init_without_rag_service(self):
        """RAGTool should initialize without RAG service (lazy init)."""
        tool = RAGTool(rag_service=None)
        assert tool._rag_service is None

    @pytest.mark.asyncio
    async def test_search_with_rag_service(self):
        """RAGTool.search() should return Evidence objects from RAG."""
        # Mock RAG service
        mock_service = MagicMock()
        mock_service.retrieve.return_value = [
            {
                "text": "Metformin shows neuroprotective properties in Alzheimer's models.",
                "score": 0.85,
                "metadata": {
                    "source": "pubmed",
                    "title": "Metformin and Alzheimer's Disease",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                    "date": "2024-01-15",
                    "authors": "Smith J, Johnson M",
                },
            },
            {
                "text": "Drug repurposing offers faster path to treatment.",
                "score": 0.72,
                "metadata": {
                    "source": "pubmed",
                    "title": "Drug Repurposing Strategies",
                    "url": "https://example.com/drug-repurposing",
                    "date": "Unknown",
                    "authors": "",
                },
            },
        ]

        tool = RAGTool(rag_service=mock_service)
        results = await tool.search("metformin alzheimer", max_results=10)

        # Assert
        assert len(results) == 2
        assert all(isinstance(e, Evidence) for e in results)
        assert results[0].citation.source == "rag"
        assert "Metformin" in results[0].citation.title
        assert results[0].relevance == 0.85
        assert "Smith J" in results[0].citation.authors
        assert results[1].citation.source == "rag"
        assert results[1].relevance == 0.72

        # Verify RAG service was called
        mock_service.retrieve.assert_called_once_with("metformin alzheimer", top_k=10)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """RAGTool.search() should return empty list when no results."""
        mock_service = MagicMock()
        mock_service.retrieve.return_value = []

        tool = RAGTool(rag_service=mock_service)
        results = await tool.search("nonexistent query")

        assert results == []
        mock_service.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_handles_missing_metadata(self):
        """RAGTool should handle documents with missing metadata gracefully."""
        mock_service = MagicMock()
        mock_service.retrieve.return_value = [
            {
                "text": "Some content",
                "score": 0.5,
                "metadata": {},  # Missing all metadata fields
            }
        ]

        tool = RAGTool(rag_service=mock_service)
        results = await tool.search("test query")

        # Should still create Evidence with defaults
        assert len(results) == 1
        assert results[0].content == "Some content"
        assert results[0].citation.title == "Untitled"
        assert results[0].citation.url == ""
        assert results[0].citation.date == "Unknown"
        assert results[0].citation.authors == []

    @pytest.mark.asyncio
    async def test_search_handles_invalid_document(self):
        """RAGTool should skip invalid documents and continue."""
        mock_service = MagicMock()
        mock_service.retrieve.return_value = [
            {
                "text": "Valid document",
                "score": 0.8,
                "metadata": {"title": "Valid", "url": "http://example.com", "date": "2024"},
            },
            {
                "text": "",  # Invalid: missing text
                "score": 0.5,
                "metadata": {"title": "Invalid"},
            },
        ]

        tool = RAGTool(rag_service=mock_service)
        results = await tool.search("test")

        # Should only return valid document
        assert len(results) == 1
        assert results[0].content == "Valid document"

    @pytest.mark.asyncio
    async def test_search_handles_rag_service_error(self):
        """RAGTool should return empty list on RAG service error."""
        mock_service = MagicMock()
        mock_service.retrieve.side_effect = Exception("RAG service error")

        tool = RAGTool(rag_service=mock_service)
        results = await tool.search("test query")

        # Should return empty list, not raise exception
        assert results == []

    @pytest.mark.asyncio
    async def test_search_lazy_initialization_success(self):
        """RAGTool should lazy-initialize RAG service when needed."""
        with patch("src.services.llamaindex_rag.get_rag_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.retrieve.return_value = [
                {
                    "text": "Test content",
                    "score": 0.9,
                    "metadata": {
                        "title": "Test",
                        "url": "http://test.com",
                        "date": "2024",
                        "authors": "Author A",
                    },
                }
            ]
            mock_get_service.return_value = mock_service

            tool = RAGTool(rag_service=None)
            results = await tool.search("test")

            assert len(results) == 1
            mock_get_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_lazy_initialization_failure(self):
        """RAGTool should return empty list if RAG service unavailable."""
        with patch("src.services.llamaindex_rag.get_rag_service") as mock_get_service:
            mock_get_service.side_effect = ConfigurationError("OPENAI_API_KEY required")

            tool = RAGTool(rag_service=None)
            results = await tool.search("test")

            assert results == []

    def test_doc_to_evidence_conversion(self):
        """RAGTool should correctly convert RAG documents to Evidence."""
        tool = RAGTool(rag_service=None)

        doc = {
            "text": "Test content here",
            "score": 0.85,
            "metadata": {
                "title": "Test Title",
                "url": "https://example.com/test",
                "date": "2024-01-15",
                "authors": "Author One, Author Two",
            },
        }

        evidence = tool._doc_to_evidence(doc)

        assert isinstance(evidence, Evidence)
        assert evidence.content == "Test content here"
        assert evidence.relevance == 0.85
        assert evidence.citation.source == "rag"
        assert evidence.citation.title == "Test Title"
        assert evidence.citation.url == "https://example.com/test"
        assert evidence.citation.date == "2024-01-15"
        assert len(evidence.citation.authors) == 2
        assert "Author One" in evidence.citation.authors
        assert "Author Two" in evidence.citation.authors

    def test_doc_to_evidence_handles_missing_fields(self):
        """RAGTool should handle missing metadata fields."""
        tool = RAGTool(rag_service=None)

        doc = {
            "text": "Content",
            "score": None,  # Missing score
            "metadata": {
                # Missing all optional fields
            },
        }

        evidence = tool._doc_to_evidence(doc)

        assert evidence.content == "Content"
        assert evidence.relevance == 0.0  # Default when score is None
        assert evidence.citation.title == "Untitled"
        assert evidence.citation.url == ""
        assert evidence.citation.date == "Unknown"
        assert evidence.citation.authors == []

    def test_doc_to_evidence_relevance_normalization(self):
        """RAGTool should normalize relevance scores to 0-1 range."""
        tool = RAGTool(rag_service=None)

        # Test score > 1.0 (should be clamped)
        doc_high = {
            "text": "Content",
            "score": 1.5,
            "metadata": {"title": "Test", "url": "", "date": "2024"},
        }
        evidence_high = tool._doc_to_evidence(doc_high)
        assert evidence_high.relevance == 1.0

        # Test score < 0.0 (should be clamped)
        doc_low = {
            "text": "Content",
            "score": -0.5,
            "metadata": {"title": "Test", "url": "", "date": "2024"},
        }
        evidence_low = tool._doc_to_evidence(doc_low)
        assert evidence_low.relevance == 0.0


class TestCreateRAGTool:
    """Tests for create_rag_tool factory function."""

    def test_create_rag_tool_with_service(self):
        """create_rag_tool should accept provided RAG service."""
        mock_service = MagicMock()
        tool = create_rag_tool(rag_service=mock_service)

        assert isinstance(tool, RAGTool)
        assert tool._rag_service == mock_service

    def test_create_rag_tool_without_service(self):
        """create_rag_tool should create tool without service (lazy init)."""
        tool = create_rag_tool(rag_service=None)

        assert isinstance(tool, RAGTool)
        assert tool._rag_service is None

    @patch("src.tools.rag_tool.RAGTool")
    def test_create_rag_tool_handles_error(self, mock_rag_tool_class):
        """create_rag_tool should raise ConfigurationError on failure."""
        mock_rag_tool_class.side_effect = Exception("Test error")

        with pytest.raises(ConfigurationError, match="Failed to create RAG tool"):
            create_rag_tool()
