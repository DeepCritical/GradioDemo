"""Shared pytest fixtures for all tests."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

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
    
    # Unset OpenAI/Anthropic keys to prevent fallback (unless explicitly set for specific tests)
    # This ensures get_model() uses HuggingFace
    if "OPENAI_API_KEY" in os.environ and os.environ.get("OPENAI_API_KEY"):
        # Only unset if it's not explicitly needed (tests can set it if needed)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if "ANTHROPIC_API_KEY" in os.environ and os.environ.get("ANTHROPIC_API_KEY"):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def mock_hf_model():
    """Create a real HuggingFace model instance for testing.
    
    This fixture provides a real HuggingFaceModel instance that uses
    the HF API/client. The InferenceClient is mocked to prevent real API calls.
    """
    from pydantic_ai.models.huggingface import HuggingFaceModel
    from pydantic_ai.providers.huggingface import HuggingFaceProvider
    
    # Create a real HuggingFace model with dummy token
    # The InferenceClient will be mocked by auto_mock_hf_inference_client
    provider = HuggingFaceProvider(api_key="dummy_token_for_testing")
    model = HuggingFaceModel("meta-llama/Llama-3.1-8B-Instruct", provider=provider)
    return model


@pytest.fixture(autouse=True)
def auto_mock_hf_inference_client(request):
    """Automatically mock HuggingFace InferenceClient to prevent real API calls.
    
    This fixture runs automatically for all tests (except OpenAI tests) and
    mocks the InferenceClient so tests use HuggingFace models but don't make
    real API calls. This allows tests to use the actual HF model/client setup
    without requiring API keys or making network requests.
    
    Tests marked with @pytest.mark.openai will skip this fixture.
    Tests can override by explicitly patching InferenceClient themselves.
    """
    # Skip auto-mocking for OpenAI tests
    if "openai" in request.keywords:
        return
    
    # Mock InferenceClient to prevent real API calls
    # This allows get_model() to create real HuggingFaceModel instances
    # but prevents actual network requests
    mock_client = MagicMock()
    mock_client.text_generation = AsyncMock(return_value="Mocked response")
    mock_client.chat_completion = AsyncMock(return_value={"choices": [{"message": {"content": "Mocked response"}}]})
    
    # Patch InferenceClient at its source (huggingface_hub)
    # This will affect all imports of InferenceClient, including in pydantic_ai
    inference_client_patch = patch("huggingface_hub.InferenceClient", return_value=mock_client)
    inference_client_patch.start()
    
    yield
    
    # Stop patch
    inference_client_patch.stop()