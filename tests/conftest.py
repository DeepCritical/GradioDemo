"""Shared pytest fixtures for all tests."""

import os
from unittest.mock import AsyncMock

import pytest

from src.utils.models import Citation, Evidence


@pytest.fixture
def mock_httpx_client(mocker):
    """Mock httpx.AsyncClient for API tests."""
    mock = mocker.patch("httpx.AsyncClient")
    mock.return_value.__aenter__ = AsyncMock(return_value=mock.return_value)
    mock.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_llm_response():
    """Factory fixture for mocking LLM responses."""

    def _mock(content: str):
        return AsyncMock(return_value=content)

    return _mock


@pytest.fixture
def sample_evidence():
    """Sample Evidence objects for testing."""
    return [
        Evidence(
            content="Metformin shows neuroprotective properties in Alzheimer's models...",
            citation=Citation(
                source="pubmed",
                title="Metformin and Alzheimer's Disease: A Systematic Review",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                date="2024-01-15",
                authors=["Smith J", "Johnson M"],
            ),
            relevance=0.85,
        ),
        Evidence(
            content="Research offers faster path to treatment discovery...",
            citation=Citation(
                source="pubmed",
                title="Research Strategies for Treatment Discovery",
                url="https://example.com/drug-repurposing",
                date="Unknown",
                authors=[],
            ),
            relevance=0.72,
        ),
    ]


# Global timeout for integration tests to prevent hanging
@pytest.fixture(scope="session", autouse=True)
def integration_test_timeout():
    """Set default timeout for integration tests."""
    # This fixture runs automatically for all tests
    # Individual tests can override with asyncio.wait_for
    pass


@pytest.fixture(autouse=True)
def default_to_huggingface(monkeypatch):
    """Ensure tests default to HuggingFace provider unless explicitly overridden.
    
    This prevents tests from requiring OpenAI/Anthropic API keys.
    Tests can override by setting LLM_PROVIDER in their environment or mocking settings.
    """
    # Only set if not already set (allows tests to override)
    if "LLM_PROVIDER" not in os.environ:
        monkeypatch.setenv("LLM_PROVIDER", "huggingface")
    
    # Set a dummy HF_TOKEN if not set (prevents errors, but tests should mock actual API calls)
    if "HF_TOKEN" not in os.environ:
        monkeypatch.setenv("HF_TOKEN", "dummy_token_for_testing")